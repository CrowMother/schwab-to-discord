
# setup_logging()
# logger.info("Application started")

# def main():
#     config = load_config()
#     db = init_database(config)
#     schwab_data = fetch_market_data(config)
#     processed = process_data(schwab_data)
#     store_results(db, processed)
#     post_to_discord(processed)

import logging

from app.models.data import load_trade

from .models.config import load_config
from .utils.logging import setup_logging
from .api.schwab import SchwabApi

logger = logging.getLogger(__name__)

def main() -> None:
    setup_logging()
    config = load_config()

    logger.info("Starting %s", config.app_name)

    client = SchwabApi(config)

    print(f"client created: {client}")

    raw_orders = client.get_orders(config)

    #load into dataclass
    for order in raw_orders:
        logger.debug(f"loading trade: {order}")
        trade = load_trade(order)
        logger.debug(f"Loaded trade: {trade}")
    
    


if __name__ == "__main__":
    main()

