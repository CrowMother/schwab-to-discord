# src/app/services/schwab_service.py
"""Schwab API service wrapper."""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import schwabdev

from app.services.base import BaseService
from app.core.errors import SchwabConnectionError, SchwabAuthError, SchwabError

if TYPE_CHECKING:
    from app.core.config import Settings


class SchwabService(BaseService):
    """
    Schwab API wrapper with retry logic.

    Provides a clean interface to the Schwab API with
    automatic token management and error handling.
    """

    def __init__(self, settings: "Settings"):
        """
        Initialize the Schwab service.

        Args:
            settings: Application settings containing Schwab credentials.
        """
        super().__init__("schwab")
        self._settings = settings
        self._client: Optional[schwabdev.Client] = None

    def _get_client(self) -> schwabdev.Client:
        """
        Get or create the Schwab client.

        Returns:
            Initialized Schwab client.

        Raises:
            SchwabAuthError: If authentication fails.
        """
        if self._client is None:
            try:
                self._client = schwabdev.Client(
                    app_key=self._settings.schwab_app_key,
                    app_secret=self._settings.schwab_app_secret,
                    callback_url=self._settings.schwab_callback_url,
                    tokens_db=self._settings.tokens_db,
                    timeout=self._settings.schwab_timeout,
                )
                self._mark_initialized()
            except Exception as e:
                raise SchwabAuthError(f"Failed to initialize Schwab client: {e}") from e

        return self._client

    @property
    def client(self) -> schwabdev.Client:
        """Get the Schwab client (lazy initialization)."""
        return self._get_client()

    def get_account_numbers(self) -> List[Dict[str, Any]]:
        """
        Get linked account numbers.

        Returns:
            List of account info dictionaries.

        Raises:
            SchwabConnectionError: If API call fails.
        """
        try:
            response = self.client.account_linked()
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise SchwabConnectionError(f"Failed to get account numbers: {e}") from e

    def get_orders(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        max_results: int = 3000,
    ) -> List[Dict[str, Any]]:
        """
        Fetch orders from all linked accounts.

        Args:
            start_date: Start of date range (defaults to time_delta_days ago).
            end_date: End of date range (defaults to now).
            status: Order status filter (e.g., "FILLED").
            max_results: Maximum number of orders to return.

        Returns:
            List of order dictionaries.

        Raises:
            SchwabConnectionError: If API call fails.
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=self._settings.time_delta_days)
        if end_date is None:
            end_date = datetime.now()
        if status is None:
            status = self._settings.order_status

        try:
            response = self.client.account_orders_all(
                fromEnteredTime=start_date,
                toEnteredTime=end_date,
                status=status,
                maxResults=max_results,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise SchwabConnectionError(f"Failed to get orders: {e}") from e

    def get_positions(self, account_hash: str) -> List[Dict[str, Any]]:
        """
        Get current positions for an account.

        Args:
            account_hash: The account hash to query.

        Returns:
            List of position dictionaries.

        Raises:
            SchwabConnectionError: If API call fails.
        """
        try:
            response = self.client.account_details(
                account_hash=account_hash,
                fields="positions"
            )
            response.raise_for_status()
            data = response.json()
            return data.get("securitiesAccount", {}).get("positions", [])
        except Exception as e:
            raise SchwabConnectionError(f"Failed to get positions: {e}") from e

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get a quote for a symbol.

        Args:
            symbol: The symbol to quote.

        Returns:
            Quote data dictionary.

        Raises:
            SchwabConnectionError: If API call fails.
        """
        try:
            response = self.client.quote(symbol)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise SchwabConnectionError(f"Failed to get quote for {symbol}: {e}") from e

    def health_check(self) -> bool:
        """
        Check if Schwab API is accessible.

        Returns:
            True if API is healthy.
        """
        try:
            self.get_account_numbers()
            return True
        except Exception as e:
            self._logger.warning(f"Schwab health check failed: {e}")
            return False
