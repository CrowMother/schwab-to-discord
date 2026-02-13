# src/app/domain/cost_basis.py
"""LIFO cost basis tracking and gain calculation."""

from __future__ import annotations

import re
import sqlite3
import logging
from typing import Optional
from dataclasses import dataclass

from app.db.cost_basis_db import (
    create_cost_basis_lot,
    get_open_lots_lifo,
    reduce_lot_quantity,
    record_lot_match,
    get_avg_gain_for_sell,
    check_sell_already_matched,
    check_buy_already_recorded,
    check_sell_unmatched,
    record_unmatched_sell,
)

logger = logging.getLogger(__name__)


@dataclass
class GainResult:
    """Result of LIFO gain calculation."""
    avg_gain_pct: float
    total_gain_amount: float
    lots_matched: int


def extract_underlying(symbol: str) -> str:
    """Extract underlying symbol from full option symbol."""
    return symbol.split()[0] if " " in symbol else symbol


def process_buy_order(
    conn: sqlite3.Connection,
    order_id: int,
    symbol: str,
    filled_quantity: float,
    price: float,
    entered_time: str
) -> bool:
    """
    Process a BUY order and create a cost basis lot.

    Args:
        conn: Database connection.
        order_id: Schwab order ID.
        symbol: Full option symbol.
        filled_quantity: Number of contracts.
        price: Price per contract.
        entered_time: Order entry timestamp.

    Returns:
        True if a new lot was created, False if already exists.
    """
    if check_buy_already_recorded(conn, order_id):
        logger.debug(f"Buy order {order_id} already recorded as lot")
        return False

    underlying = extract_underlying(symbol)
    lot_id = create_cost_basis_lot(
        conn=conn,
        order_id=order_id,
        symbol=symbol,
        underlying=underlying,
        quantity=filled_quantity,
        avg_cost=price,
        entered_time=entered_time
    )
    logger.info(f"Created cost basis lot {lot_id} for {symbol}: {filled_quantity} @ ${price}")
    return True


def process_sell_order(
    conn: sqlite3.Connection,
    order_id: int,
    symbol: str,
    filled_quantity: float,
    sell_price: float
) -> Optional[GainResult]:
    """
    Process a SELL order using LIFO matching against open lots.

    Matches sells against the newest (LIFO) open lots first.

    Args:
        conn: Database connection.
        order_id: Schwab order ID.
        symbol: Full option symbol.
        filled_quantity: Number of contracts sold.
        sell_price: Sell price per contract.

    Returns:
        GainResult with average gain %, or None if no lots to match.
    """
    if check_sell_already_matched(conn, order_id):
        avg_gain = get_avg_gain_for_sell(conn, order_id)
        if avg_gain is not None:
            return GainResult(avg_gain_pct=avg_gain, total_gain_amount=0, lots_matched=0)
        return None

    if check_sell_unmatched(conn, order_id):
        return None

    open_lots = get_open_lots_lifo(conn, symbol)

    if not open_lots:
        logger.warning(f"No open lots found for {symbol} to match sell order {order_id}")
        record_unmatched_sell(conn, order_id, symbol, filled_quantity, sell_price)
        return None

    remaining_to_sell = filled_quantity
    total_gain_amount = 0.0
    total_weighted_gain = 0.0
    total_qty_matched = 0.0
    lots_matched = 0

    for lot in open_lots:
        if remaining_to_sell <= 0:
            break

        lot_id, _, lot_symbol, lot_qty, lot_remaining, lot_cost, _ = lot

        qty_from_lot = min(remaining_to_sell, lot_remaining)

        # Options: price per contract * 100 shares
        cost_for_qty = qty_from_lot * lot_cost * 100
        revenue_for_qty = qty_from_lot * sell_price * 100
        gain_amount = revenue_for_qty - cost_for_qty

        if lot_cost > 0:
            gain_pct = ((sell_price - lot_cost) / lot_cost) * 100
        else:
            gain_pct = 0.0

        record_lot_match(
            conn=conn,
            sell_order_id=order_id,
            lot_id=lot_id,
            quantity=qty_from_lot,
            cost_basis=lot_cost,
            sell_price=sell_price,
            gain_pct=gain_pct,
            gain_amount=gain_amount
        )

        reduce_lot_quantity(conn, lot_id, qty_from_lot)

        total_weighted_gain += gain_pct * qty_from_lot
        total_qty_matched += qty_from_lot
        total_gain_amount += gain_amount
        lots_matched += 1
        remaining_to_sell -= qty_from_lot

        logger.info(f"Matched {qty_from_lot} from lot {lot_id} (cost ${lot_cost}) -> {gain_pct:.2f}% gain")

    conn.commit()

    if total_qty_matched > 0:
        avg_gain_pct = total_weighted_gain / total_qty_matched
        return GainResult(
            avg_gain_pct=avg_gain_pct,
            total_gain_amount=total_gain_amount,
            lots_matched=lots_matched
        )

    return None


def get_gain_for_order(conn: sqlite3.Connection, order_id: int) -> Optional[float]:
    """Get the average gain percentage for a sell order (if already matched)."""
    return get_avg_gain_for_sell(conn, order_id)


def parse_strike_display(description: str) -> str:
    """
    Parse option description to extract strike display.

    Args:
        description: Option description like "ORACLE CORP 02/13/2026 $149 Call"

    Returns:
        Strike display like "149c" or "267.5p"
    """
    if not description:
        return "N/A"

    parts = description.strip().split()
    if len(parts) < 2:
        return description

    option_type = parts[-1].lower()
    strike_raw = parts[-2] if len(parts) >= 2 else "?"
    strike = strike_raw.lstrip('$')

    if option_type == "call":
        return f"{strike}c"
    elif option_type == "put":
        return f"{strike}p"
    else:
        return description


def parse_expiration(description: str) -> str:
    """
    Parse option description to extract expiration date.

    Args:
        description: Option description like "ORACLE CORP 02/13/2026 $149 Call"

    Returns:
        Expiration date like "02/13/2026"
    """
    if not description:
        return "N/A"

    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', description)
    if date_match:
        return date_match.group(1)

    return "N/A"
