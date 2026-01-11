import schwabdev
import logging

logger = logging.getLogger(__name__)

class SchwabApi:
    def __init__(self, app_key: str, app_secret: str):
        logging.debug("Initializing Schwabdev client")
        self.client = schwabdev.Client(app_key,
                                        app_secret,
                                        callback_url="https://127.0.0.1",
                                        tokens_db="tokens.db",
                                        timeout=10,
                                        call_on_auth=None)

    def get_orders(self, start_iso: str, end_iso: str, status: str | None = None):
        # adapt args to the schwabdev method you’re using
        resp = self.client.account_orders_all(start_iso, end_iso, None, status)
        resp.raise_for_status()
        return resp.json()
