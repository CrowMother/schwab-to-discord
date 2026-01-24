import os
import sqlite3
import json
import logging

from app.db.trades_db import init_trades_db
from app.db.trade_state_db import init_trade_state_db
from app.db.trades_repo import (
    store_trade_fill,
    update_position_state,
    fetch_unposted_fills,
    mark_posted,
)

from app.models.fill_trade import FillTrade


from app.discord.discord_message import build_discord_message_template
from app.discord.discord_webhook import post_webhook

from .models.config import load_single_value, load_config
from .utils.logging import setup_logging
from .api.schwab import SchwabApi

logger = logging.getLogger(__name__)


def extract_fill_trades(raw_orders):
    for order in raw_orders or []:
        account_number = str(order.get("accountNumber") or "")
        order_id = order.get("orderId")
        status = order.get("status")
        entered_time = order.get("enteredTime")
        close_time = order.get("closeTime")

        if not account_number or order_id is None:
            continue

        legs = order.get("orderLegCollection") or []
        activities = order.get("orderActivityCollection") or []

        leg_by_id = {leg.get("legId"): leg for leg in legs if isinstance(leg.get("legId"), int)}

        for act in activities:
            if act.get("executionType") != "FILL":
                continue

            for ex in (act.get("executionLegs") or []):
                ex_qty = ex.get("quantity")
                ex_price = ex.get("price")
                ex_time = ex.get("time")
                ex_leg_id = ex.get("legId")

                if ex_qty is None or ex_time is None:
                    continue

                leg = leg_by_id.get(ex_leg_id) if isinstance(ex_leg_id, int) else (legs[0] if len(legs) == 1 else None)
                if not leg:
                    continue

                inst = (leg.get("instrument") or {})
                instrument_id = inst.get("instrumentId")
                symbol = inst.get("symbol") or ""
                asset_type = inst.get("assetType") or ""
                instruction = leg.get("instruction") or ""
                position_effect = leg.get("positionEffect")
                description = inst.get("description") or order.get("description")

                if not isinstance(instrument_id, int) or not symbol or not asset_type or not instruction:
                    continue

                yield FillTrade(
                    account_number=account_number,
                    instrument_id=instrument_id,
                    order_id=int(order_id),
                    leg_id=int(ex_leg_id) if isinstance(ex_leg_id, int) else None,
                    execution_time=str(ex_time),

                    symbol=str(symbol),
                    asset_type=str(asset_type),
                    instruction=str(instruction),
                    position_effect=str(position_effect) if position_effect else None,

                    fill_quantity=float(ex_qty),
                    fill_price=float(ex_price) if ex_price is not None else None,

                    status=str(status) if status else None,
                    description=str(description) if description else None,
                    entered_time=str(entered_time) if entered_time else None,
                    close_time=str(close_time) if close_time else None,
                )



def ingest_fills(conn, raw_orders):
    with conn:  # transaction
        for ft in extract_fill_trades(raw_orders):
            trade_id = store_trade_fill(conn, ft)
            update_position_state(conn, trade_id, ft)


def send_unposted(conn, config):
    template = load_single_value("TEMPLATE", None)

    rows = fetch_unposted_fills(conn, limit=200)
    for row in rows:
        # expected row order from fetch_unposted_fills:
        # trade_id, symbol, instruction, asset_type, position_effect,
        # fill_quantity, fill_price, status, description, execution_time,
        # account_number, instrument_id, order_id, leg_id
        trade_id = row[0]

        # make a lightweight object for template formatting
        class T: pass
        t = T()
        t.symbol = row[1]
        t.instruction = row[2]
        t.asset_type = row[3]
        t.status = row[7]
        t.description = row[8]
        t.entered_time = None
        t.close_time = None

        # map fill quantities to your template names
        t.quantity = row[5]
        t.filled_quantity = row[5]
        t.remaining_quantity = None
        t.price = row[6]

        msg = build_discord_message_template(template, t) if template else (
            f"**{t.symbol}** {t.instruction} ({t.asset_type})\n"
            f"Qty: {t.quantity} @ {t.price or 'N/A'} | {row[4] or 'N/A'}\n"
            f"{t.description or ''}"
        )

        resp = post_webhook(config.discord_webhook, msg, timeout=config.schwab_timeout)
        logger.debug("Posted trade_id=%s response=%s", trade_id, resp)

        with conn:
            mark_posted(conn, trade_id, discord_message_id=None)


def main() -> None:
    setup_logging()
    config = load_config()

    os.makedirs(os.path.dirname(config.db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(config.db_path)
    init_trades_db(config.db_path, conn)
    init_trade_state_db(config.db_path, conn)

    logger.info("Starting %s", config.app_name)

    client = SchwabApi(config)
    raw_orders = client.get_orders(config)

    # debug save raw orders
    with open("debug_raw_orders.json", "w") as f:
        json.dump(raw_orders, f, indent=4)

    ingest_fills(conn, raw_orders)
    send_unposted(conn, config)

    conn.close()


if __name__ == "__main__":
    main()
