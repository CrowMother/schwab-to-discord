import os
import sqlite3
import time
from app.db.trades_db import init_trades_db
from app.db.trade_state_db import init_trade_state_db
from app.db.queries import get_unposted_trade_ids

import logging

from app.db.trades_repo import ensure_trade_state, load_trade_from_db, mark_posted, store_trade
from app.discord.discord_message import build_discord_message, build_discord_message_template
from app.discord.discord_webhook import post_webhook
from app.models.data import load_trade

from .models.config import load_single_value, load_config
from .utils.logging import setup_logging
from .api.schwab import SchwabApi

logger = logging.getLogger(__name__)

def get_schwab_positions(client):
    """Fetch current positions from Schwab account."""
    try:
        resp = client.client.account_details_all(fields="positions")
        resp.raise_for_status()
        accounts = resp.json()

        positions_by_symbol = {}
        for account in accounts:
            account_positions = account.get("securitiesAccount", {}).get("positions", [])
            for pos in account_positions:
                instrument = pos.get("instrument", {})
                asset_type = instrument.get("assetType", "N/A")
                if asset_type != "OPTION":
                    continue

                symbol = instrument.get("symbol", "N/A")
                qty = pos.get("longQuantity", 0) - pos.get("shortQuantity", 0)

                underlying = symbol.split()[0] if " " in symbol else symbol
                if underlying not in positions_by_symbol:
                    positions_by_symbol[underlying] = 0
                positions_by_symbol[underlying] += qty

        return positions_by_symbol
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        return {}

def get_total_sold(conn, symbol):
    """Get total quantity sold for a symbol from trade history."""
    try:
        underlying = symbol.split()[0] if " " in symbol else symbol
        cursor = conn.execute("""
            SELECT SUM(filled_quantity) FROM trades
            WHERE symbol LIKE ? AND instruction LIKE '%SELL%'
        """, (f"{underlying}%",))
        result = cursor.fetchone()[0]
        return int(result) if result else 0
    except Exception as e:
        logger.error(f"Error getting total sold: {e}")
        return 0

def load_trade_orders(raw_orders=None, conn=None):
    for order in raw_orders:
        logger.debug(f"loading trade: {order}")
        trade = load_trade(order)
        logger.debug(f"Loaded trade: {trade}")

        trade_id = store_trade(conn, trade)
        logger.debug(f"Stored trade with ID: {trade_id}")
        ensure_trade_state(conn, trade_id)

    conn.commit()

def send_unposted_trades(conn, config, unposted_trade_ids, positions_by_symbol):
    for trade_id in unposted_trade_ids:
        trade = load_trade_from_db(conn, trade_id)
        if not trade:
            continue

        template = load_single_value("TEMPLATE", None)
        if template:
            template = template.replace("\n", "\n")

        # Get position data
        underlying = trade.symbol.split()[0] if " " in trade.symbol else trade.symbol
        position_left = positions_by_symbol.get(underlying, 0)
        total_sold = get_total_sold(conn, trade.symbol)

        # build message with position data
        msg = build_discord_message_template(template, trade, position_left=position_left, total_sold=total_sold)

        # Post to primary webhook
        resp = post_webhook(config.discord_webhook, msg, timeout=config.schwab_timeout)
        logger.debug(f"Posted trade ID {trade_id} to Discord (primary), response: {resp}")

        # Post to secondary webhook if configured
        webhook_2 = load_single_value("DISCORD_WEBHOOK_2", None)
        if webhook_2:
            resp2 = post_webhook(webhook_2, msg, timeout=config.schwab_timeout)
            logger.debug(f"Posted trade ID {trade_id} to Discord (secondary), response: {resp2}")

        with conn:
            mark_posted(conn, trade_id, discord_message_id=None)
    conn.commit()


def main() -> None:
    config = load_config()
    setup_logging()

    os.makedirs(os.path.dirname(config.db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(config.db_path)
    init_trades_db(config.db_path, conn)
    init_trade_state_db(config.db_path, conn)

    logger.info("Starting %s", config.app_name)

    client = SchwabApi(config)

    print(f"client created: {client}")

    while True:
        try:
            raw_orders = client.get_orders(config)
            load_trade_orders(raw_orders, conn)

            # Get current positions from Schwab
            positions_by_symbol = get_schwab_positions(client)

            unposted_trade_ids = get_unposted_trade_ids(conn)
            send_unposted_trades(conn, config, unposted_trade_ids, positions_by_symbol)

            time.sleep(5)
        except Exception as e:
            logger.error(f"Error in main loop (rebooting after 10 seconds): {e}", exc_info=True)
            time.sleep(10)
            break
    conn.close()

if __name__ == "__main__":
    main()
