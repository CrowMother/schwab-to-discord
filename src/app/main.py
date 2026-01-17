
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
from app.discord.discord_message import build_discord_message
from app.discord.discord_webhook import post_webhook
from app.models.data import load_trade

from .models.config import load_config
from .utils.logging import setup_logging
from .api.schwab import SchwabApi
from app.models import config

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

    #load into dataclass
    for order in raw_orders:
        logger.debug(f"loading trade: {order}")
        trade = load_trade(order)
        logger.debug(f"Loaded trade: {trade}")

        # store trade
        trade_id = store_trade(conn, trade)
        logger.debug(f"Stored trade with ID: {trade_id}")
        ensure_trade_state(conn, trade_id)
    
    conn.commit()

    #pull unposted trades

    unposted_trade_ids = get_unposted_trade_ids(conn)

    for trade_id in unposted_trade_ids:
        trade = load_trade_from_db(conn, trade_id)
        if not trade:
            continue

        msg = build_discord_message(trade)
        resp = post_webhook(config.discord_webhook, msg, timeout=config.schwab_timeout)

        with conn:
            mark_posted(conn, trade_id, discord_message_id=None)

    
        # normailze / format trade for discord
        
        # post to discord
        
    # Figure out if I want to create a list for all these trades or process them directly after loading

    conn.commit()
    conn.close()
    # After figuring out data flow, implement storing to DB 
    # Figure out DB schema or how to make it flexible to structure changes
    # 
    # and then posting to Discord

if __name__ == "__main__":
    main()

