
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

from .config import load_config
from .utils.logging import setup_logging
from .api.schwab import SchwabApi

logger = logging.getLogger(__name__)

def main() -> None:
    setup_logging()
    config = load_config()

    logger.info("Starting %s", config.app_name)

    client = SchwabApi(config.schwab_app_key, config.schwab_app_secret)

    print(f"client created: {client}")

if __name__ == "__main__":
    main()

