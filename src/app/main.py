
# setup_logging()
# logger.info("Application started")

# def main():
#     config = load_config()
#     db = init_database(config)
#     schwab_data = fetch_market_data(config)
#     processed = process_data(schwab_data)
#     store_results(db, processed)
#     post_to_discord(processed)
import os
import sqlite3
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

def load_trade_orders(raw_orders=None, conn=None):
        for order in raw_orders:
            logger.debug(f"loading trade: {order}")
            trade = load_trade(order)
            logger.debug(f"Loaded trade: {trade}")

            # store trade
            trade_id = store_trade(conn, trade)
            logger.debug(f"Stored trade with ID: {trade_id}")
            ensure_trade_state(conn, trade_id)
        
        conn.commit()

def send_unposted_trades(conn, config, unposted_trade_ids):
    for trade_id in unposted_trade_ids:
        # load trade
        trade = load_trade_from_db(conn, trade_id)
        if not trade:
            continue
        
        template = load_single_value("TEMPLATE", None)
        #build message
        msg = build_discord_message_template(template, trade)
        #post to discord
        resp = post_webhook(config.discord_webhook, msg, timeout=config.schwab_timeout)
        logger.debug(f"Posted trade ID {trade_id} to Discord, response: {resp}")
        #mark posted
        with conn:
            mark_posted(conn, trade_id, discord_message_id=None)         
    # Figure out if I want to create a list for all these trades or process them directly after loading
    conn.commit()
    conn.close()


logger = logging.getLogger(__name__)

def main() -> None:
    setup_logging()
    config = load_config()

    #create conn
    os.makedirs(os.path.dirname(config.db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(config.db_path)
    init_trades_db(config.db_path, conn)
    init_trade_state_db(config.db_path, conn)

    logger.info("Starting %s", config.app_name)

    client = SchwabApi(config)

    print(f"client created: {client}")

    raw_orders = client.get_orders(config)
    #load into database
    load_trade_orders(raw_orders, conn)
    
    #pull unposted trades and send to discord
    unposted_trade_ids = get_unposted_trade_ids(conn)
    send_unposted_trades(conn, config, unposted_trade_ids)

if __name__ == "__main__":
    main()

