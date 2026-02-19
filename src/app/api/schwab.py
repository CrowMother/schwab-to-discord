# src/app/api/schwab.py
"""Schwab API client with retry logic."""

from __future__ import annotations

import time
import logging
from typing import List, Any, TYPE_CHECKING

import schwabdev
from requests.exceptions import RequestException, ConnectionError, Timeout

from app.utils.time import time_delta_to_iso_days
from app.constants import Defaults

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)


class SchwabApiError(Exception):
    """Raised when Schwab API operations fail after retries."""
    pass


def _retry_with_backoff(func, max_retries: int = Defaults.MAX_RETRIES,
                        base_delay: int = Defaults.RETRY_DELAY_BASE):
    """
    Decorator-style helper that retries a function with exponential backoff.

    Args:
        func: Function to call
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (doubles each retry)

    Returns:
        Result of the function call

    Raises:
        SchwabApiError: If all retries fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return func()
        except (ConnectionError, Timeout) as e:
            last_exception = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Network error on attempt {attempt + 1}/{max_retries + 1}: {e}")
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries + 1} attempts failed")
        except RequestException as e:
            last_exception = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Request error on attempt {attempt + 1}/{max_retries + 1}: {e}")
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries + 1} attempts failed")

    raise SchwabApiError(f"API call failed after {max_retries + 1} attempts: {last_exception}")


class SchwabApi:
    """Wrapper around schwabdev client with retry logic."""

    def __init__(self, config: "Settings"):
        """
        Initialize Schwab API client.

        Args:
            config: Application settings with Schwab credentials
        """
        logger.debug("Initializing Schwabdev client")
        self.client = schwabdev.Client(
            app_key=config.schwab_app_key,
            app_secret=config.schwab_app_secret,
            callback_url=config.callback_url,  # Uses property alias
            tokens_db=config.tokens_db,
            timeout=config.schwab_timeout,
            call_on_auth=config.call_on_auth
        )
        self._config = config

    def get_orders(self, config: "Settings" = None) -> List[Any]:
        """
        Fetch orders from Schwab with retry logic.

        Args:
            config: Optional config override (uses init config if not provided)

        Returns:
            List of order dictionaries from Schwab API

        Raises:
            SchwabApiError: If all retries fail
        """
        cfg = config or self._config
        start_iso, end_iso = time_delta_to_iso_days(cfg.time_delta_days)

        def _fetch():
            resp = self.client.account_orders_all(start_iso, end_iso, None, cfg.status)
            resp.raise_for_status()
            return resp.json()

        return _retry_with_backoff(_fetch)

    def get_account_details(self, fields: str = "positions") -> dict:
        """
        Fetch account details from Schwab with retry logic.

        Args:
            fields: Fields to include (e.g., "positions")

        Returns:
            Account details dictionary

        Raises:
            SchwabApiError: If all retries fail
        """
        def _fetch():
            resp = self.client.account_details_all(fields=fields)
            resp.raise_for_status()
            return resp.json()

        return _retry_with_backoff(_fetch)
