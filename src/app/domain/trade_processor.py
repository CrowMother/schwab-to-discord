# src/app/domain/trade_processor.py
"""Trade processing - fetches from Schwab and stores in database."""

from __future__ import annotations

import sqlite3
import logging
from typing import TYPE_CHECKING, List, Optional

from app.models.data import Trade, load_trade
from app.db.trades_repo import store_trade, ensure_trade_state
from app.domain.cost_basis import process_buy_order, process_sell_order

if TYPE_CHECKING:
    from app.services.schwab_service import SchwabService

logger = logging.getLogger(__name__)


class TradeProcessor:
    """
    Handles polling Schwab and storing trades.

    Responsible for:
    - Fetching orders from Schwab API
    - Converting raw orders to Trade objects
    - Storing trades in the database
    - Processing cost basis for buy/sell orders
    """

    def __init__(self, schwab: "SchwabService", db_path: str):
        """
        Initialize the trade processor.

        Args:
            schwab: Schwab service for API calls.
            db_path: Path to the trades database.
        """
        self.schwab = schwab
        self.db_path = db_path
        self.logger = logging.getLogger("domain.trade_processor")

    def poll_and_store(self, conn: sqlite3.Connection) -> List[Trade]:
        """
        Fetch orders from Schwab and store new ones.

        Args:
            conn: Database connection.

        Returns:
            List of newly stored trades.
        """
        raw_orders = self.schwab.get_orders()
        return self.process_orders(conn, raw_orders)

    def process_orders(
        self,
        conn: sqlite3.Connection,
        raw_orders: List[dict]
    ) -> List[Trade]:
        """
        Process raw Schwab orders into the database.

        Args:
            conn: Database connection.
            raw_orders: List of raw order dictionaries from Schwab.

        Returns:
            List of processed trades.
        """
        new_trades = []

        for order in raw_orders:
            try:
                trade = self._process_single_order(conn, order)
                if trade:
                    new_trades.append(trade)
            except Exception as e:
                order_id = order.get('orderId', 'unknown')
                self.logger.error(f"Error processing order {order_id}: {e}")

        conn.commit()
        return new_trades

    def _process_single_order(
        self,
        conn: sqlite3.Connection,
        order: dict
    ) -> Optional[Trade]:
        """
        Process a single order.

        Args:
            conn: Database connection.
            order: Raw order dictionary.

        Returns:
            Trade if processed, None if skipped.
        """
        trade = load_trade(order)
        trade_id = store_trade(conn, trade)
        ensure_trade_state(conn, trade_id)

        # Process cost basis for LIFO tracking
        if trade.instruction and trade.order_id:
            self._process_cost_basis(conn, trade)

        return trade

    def _process_cost_basis(self, conn: sqlite3.Connection, trade: Trade) -> None:
        """
        Process cost basis for a trade.

        Args:
            conn: Database connection.
            trade: The trade to process.
        """
        instruction = trade.instruction.upper() if trade.instruction else ""

        if "BUY" in instruction:
            process_buy_order(
                conn=conn,
                order_id=trade.order_id,
                symbol=trade.symbol,
                filled_quantity=trade.filled_quantity,
                price=trade.price,
                entered_time=trade.entered_time or ""
            )
        elif "SELL" in instruction:
            process_sell_order(
                conn=conn,
                order_id=trade.order_id,
                symbol=trade.symbol,
                filled_quantity=trade.filled_quantity,
                sell_price=trade.price
            )
