# src/app/api/positions.py
"""Shared module for fetching Schwab positions."""

from __future__ import annotations
import os
import logging
from typing import Optional, Tuple, List, Dict, Any

from app.cost_basis import extract_underlying

logger = logging.getLogger(__name__)


def get_schwab_positions(client=None) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Fetch current positions from Schwab account.

    Args:
        client: Optional SchwabApi client. If not provided, creates one using env vars.

    Returns:
        Tuple of (positions_list, positions_by_symbol_dict)
        - positions_list: List of position dicts with symbol, asset_type, quantity, avg_price, market_value
        - positions_by_symbol: Dict mapping underlying symbol to total quantity
    """
    try:
        # If no client provided, create one using schwabdev directly
        if client is None:
            import schwabdev
            client_obj = schwabdev.Client(
                app_key=os.getenv("SCHWAB_APP_KEY"),
                app_secret=os.getenv("SCHWAB_APP_SECRET"),
                callback_url=os.getenv("CALLBACK_URL"),
                tokens_db=os.getenv("TOKENS_DB", "/data/tokens.db"),
                timeout=int(os.getenv("SCHWAB_TIMEOUT", 10))
            )
            resp = client_obj.account_details_all(fields="positions")
        else:
            # Use the provided client (SchwabApi wrapper)
            resp = client.client.account_details_all(fields="positions")

        resp.raise_for_status()
        accounts = resp.json()

        positions = []
        positions_by_symbol = {}

        for account in accounts:
            account_positions = account.get("securitiesAccount", {}).get("positions", [])
            for pos in account_positions:
                instrument = pos.get("instrument", {})
                asset_type = instrument.get("assetType", "N/A")

                # Only include options, skip equity
                if asset_type != "OPTION":
                    continue

                symbol = instrument.get("symbol", "N/A")
                qty = pos.get("longQuantity", 0) - pos.get("shortQuantity", 0)

                positions.append({
                    "symbol": symbol,
                    "asset_type": asset_type,
                    "quantity": qty,
                    "avg_price": pos.get("averagePrice", 0),
                    "market_value": pos.get("marketValue", 0),
                })

                # Build lookup by underlying symbol
                underlying = extract_underlying(symbol)
                if underlying not in positions_by_symbol:
                    positions_by_symbol[underlying] = 0
                positions_by_symbol[underlying] += qty

        return positions, positions_by_symbol

    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        return [], {}
