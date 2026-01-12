import schwabdev
import logging
from app.utils.time import time_delta_to_iso_days

from app.models.config import Config

logger = logging.getLogger(__name__)

class SchwabApi:
    def __init__(self, config: Config):
        logging.debug("Initializing Schwabdev client")
        self.client = schwabdev.Client(app_key=config.schwab_app_key,
                                        app_secret=config.schwab_app_secret,
                                        callback_url=config.callback_url,
                                        tokens_db=config.tokens_db,
                                        timeout=config.schwab_timeout,
                                        call_on_auth=config.call_on_auth)

    def get_orders(self, config: Config):
        # adapt args to the schwabdev method you’re using
        start_iso, end_iso = time_delta_to_iso_days(config.time_delta_days)
        resp = self.client.account_orders_all(start_iso, end_iso, None, config.status)
        resp.raise_for_status()
        return resp.json()
