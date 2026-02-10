import os
import sqlite3
import time
from app.db.trades_db import init_trades_db
from app.db.trade_state_db import init_trade_state_db
from app.db.cost_basis_db import init_cost_basis_db
from app.db.queries import get_unposted_trade_ids

import logging

from app.db.trades_repo import ensure_trade_state, load_trade_from_db, mark_posted, store_trade
from app.discord.discord_message import build_option_bot_message
from app.discord.discord_webhook import post_webhook
from app.models.data import load_trade
from app.cost_basis import process_buy_order, process_sell_order, get_gain_for_order, extract_underlying
from app.db.cost_basis_db import get_matches_for_sell
from app.api.positions import get_schwab_positions

from .models.config import load_single_value, load_config
from .utils.logging import setup_logging
from .api.schwab import SchwabApi
from .scheduler import start_gsheet_scheduler, stop_gsheet_scheduler
from export_trades import export_trades

logger = logging.getLogger(__name__)

def get_total_sold(conn, symbol):
    """Get total quantity sold for an exact symbol from trade history."""
    try:
        cursor = conn.execute("""
            SELECT SUM(filled_quantity) FROM trades
            WHERE symbol = ? AND instruction LIKE '%SELL%'
        """, (symbol,))
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

        # Process cost basis for FIFO tracking
        if trade.instruction and trade.order_id:
            if "BUY" in trade.instruction.upper():
                process_buy_order(
                    conn=conn,
                    order_id=trade.order_id,
                    symbol=trade.symbol,
                    filled_quantity=trade.filled_quantity,
                    price=trade.price,
                    entered_time=trade.entered_time or ""
                )
            elif "SELL" in trade.instruction.upper():
                process_sell_order(
                    conn=conn,
                    order_id=trade.order_id,
                    symbol=trade.symbol,
                    filled_quantity=trade.filled_quantity,
                    sell_price=trade.price
                )

    conn.commit()

def send_unposted_trades(conn, config, unposted_trade_ids, positions_by_symbol):
    for trade_id in unposted_trade_ids:
        trade = load_trade_from_db(conn, trade_id)
        if not trade:
            continue

        # Get position data - use underlying for position lookup
        position_left = positions_by_symbol.get(trade.underlying, 0)
        total_sold = get_total_sold(conn, trade.symbol)

        # Get gain percentage for sell orders only
        gain_pct = None
        entry_price = None
        if trade.instruction and "SELL" in trade.instruction.upper() and trade.order_id:
            gain_pct = get_gain_for_order(conn, trade.order_id)
            # Get entry price from lot matches if available
            matches = get_matches_for_sell(conn, trade.order_id)
            if matches:
                # Weighted average entry price
                total_qty = sum(m[2] for m in matches)
                if total_qty > 0:
                    entry_price = sum(m[2] * m[3] for m in matches) / total_qty

        # Build message using Option Bot format (different for BUY vs SELL)
        msg = build_option_bot_message(
            trade,
            position_left=position_left,
            total_sold=total_sold,
            gain_pct=gain_pct,
            entry_price=entry_price
        )

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
    init_cost_basis_db(config.db_path, conn)

    logger.info("Starting %s", config.app_name)

    # Start weekly Google Sheets export scheduler (default: Sundays at 8:00 PM)
    try:
        start_gsheet_scheduler()
        logger.info("Weekly Google Sheets export scheduler started")
    except Exception as e:
        logger.warning(f"Could not start Google Sheets scheduler: {e}")

    client = SchwabApi(config)

    logger.info(f"Client created: {client}")

    while True:
        try:
            raw_orders = client.get_orders(config)
            load_trade_orders(raw_orders, conn)

            # Get current positions from Schwab
            _, positions_by_symbol = get_schwab_positions(client)

            unposted_trade_ids = get_unposted_trade_ids(conn)
            send_unposted_trades(conn, config, unposted_trade_ids, positions_by_symbol)

            # Auto-export to Excel when new trades are processed
            if unposted_trade_ids:
                try:
                    export_trades()
                    logger.info(f"Excel export completed for {len(unposted_trade_ids)} new trades")
                except Exception as e:
                    logger.warning(f"Excel export failed: {e}")

            time.sleep(5)
        except Exception as e:
            logger.error(f"Error in main loop (rebooting after 10 seconds): {e}", exc_info=True)
            time.sleep(10)
            break

    # Cleanup
    stop_gsheet_scheduler()
    conn.close()

if __name__ == "__main__":
    main()
