import schwabdev

class SchwabApi:
    def __init__(self, app_key: str, app_secret: str):
        self.client = schwabdev.Client(app_key, app_secret)

    def get_orders(self, start_iso: str, end_iso: str, status: str | None = None):
        # adapt args to the schwabdev method you’re using
        resp = self.client.account_orders_all(start_iso, end_iso, None, status)
        resp.raise_for_status()
        return resp.json()