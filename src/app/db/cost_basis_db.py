# src/app/db/cost_basis_db.py
"""Database tables for FIFO cost basis tracking."""

from __future__ import annotations
import sqlite3
from typing import Optional


def init_cost_basis_db(db_path: str, conn: Optional[sqlite3.Connection] = None) -> None:
    """Initialize cost basis tracking tables."""
    should_close = conn is None
    if conn is None:
        conn = sqlite3.connect(db_path)

    try:
        # Table for tracking buy order lots (each order = 1 lot)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cost_basis_lots (
                lot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL UNIQUE,
                symbol TEXT NOT NULL,
                underlying TEXT NOT NULL,
                quantity REAL NOT NULL,
                remaining_qty REAL NOT NULL,
                avg_cost REAL NOT NULL,
                entered_time TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES trades(order_id)
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_lots_underlying_remaining
            ON cost_basis_lots(underlying, remaining_qty)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_lots_entered_time
            ON cost_basis_lots(entered_time)
        """)

        # Table for tracking FIFO matches when selling
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lot_matches (
                match_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sell_order_id INTEGER NOT NULL,
                lot_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                cost_basis REAL NOT NULL,
                sell_price REAL NOT NULL,
                gain_pct REAL NOT NULL,
                gain_amount REAL NOT NULL,
                matched_at TEXT NOT NULL,
                FOREIGN KEY (sell_order_id) REFERENCES trades(order_id),
                FOREIGN KEY (lot_id) REFERENCES cost_basis_lots(lot_id)
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_matches_sell_order
            ON lot_matches(sell_order_id)
        """)

        conn.commit()
    finally:
        if should_close:
            conn.close()


def create_cost_basis_lot(conn: sqlite3.Connection, order_id: int, symbol: str,
                          underlying: str, quantity: float, avg_cost: float,
                          entered_time: str) -> int:
    """Create a new cost basis lot from a BUY order."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    cursor = conn.execute("""
        INSERT OR IGNORE INTO cost_basis_lots
        (order_id, symbol, underlying, quantity, remaining_qty, avg_cost, entered_time, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (order_id, symbol, underlying, quantity, quantity, avg_cost, entered_time, now))

    conn.commit()
    return cursor.lastrowid


def get_open_lots_fifo(conn: sqlite3.Connection, underlying: str) -> list:
    """Get all open lots for an underlying symbol in FIFO order (oldest first)."""
    cursor = conn.execute("""
        SELECT lot_id, order_id, symbol, quantity, remaining_qty, avg_cost, entered_time
        FROM cost_basis_lots
        WHERE underlying = ? AND remaining_qty > 0
        ORDER BY entered_time ASC
    """, (underlying,))
    return cursor.fetchall()


def reduce_lot_quantity(conn: sqlite3.Connection, lot_id: int, sold_qty: float) -> None:
    """Reduce remaining quantity in a lot after a sale."""
    conn.execute("""
        UPDATE cost_basis_lots
        SET remaining_qty = remaining_qty - ?
        WHERE lot_id = ?
    """, (sold_qty, lot_id))


def record_lot_match(conn: sqlite3.Connection, sell_order_id: int, lot_id: int,
                     quantity: float, cost_basis: float, sell_price: float,
                     gain_pct: float, gain_amount: float) -> int:
    """Record a FIFO match between a sell order and a cost basis lot."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    cursor = conn.execute("""
        INSERT INTO lot_matches
        (sell_order_id, lot_id, quantity, cost_basis, sell_price, gain_pct, gain_amount, matched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (sell_order_id, lot_id, quantity, cost_basis, sell_price, gain_pct, gain_amount, now))

    return cursor.lastrowid


def get_matches_for_sell(conn: sqlite3.Connection, sell_order_id: int) -> list:
    """Get all lot matches for a sell order."""
    cursor = conn.execute("""
        SELECT match_id, lot_id, quantity, cost_basis, sell_price, gain_pct, gain_amount
        FROM lot_matches
        WHERE sell_order_id = ?
    """, (sell_order_id,))
    return cursor.fetchall()


def get_avg_gain_for_sell(conn: sqlite3.Connection, sell_order_id: int) -> Optional[float]:
    """Get weighted average gain percentage for a sell order."""
    cursor = conn.execute("""
        SELECT SUM(quantity * gain_pct) / SUM(quantity) as avg_gain
        FROM lot_matches
        WHERE sell_order_id = ?
    """, (sell_order_id,))
    result = cursor.fetchone()
    return result[0] if result and result[0] is not None else None


def check_sell_already_matched(conn: sqlite3.Connection, sell_order_id: int) -> bool:
    """Check if a sell order has already been matched."""
    cursor = conn.execute("""
        SELECT COUNT(*) FROM lot_matches WHERE sell_order_id = ?
    """, (sell_order_id,))
    return cursor.fetchone()[0] > 0


def check_buy_already_recorded(conn: sqlite3.Connection, order_id: int) -> bool:
    """Check if a buy order has already been recorded as a lot."""
    cursor = conn.execute("""
        SELECT COUNT(*) FROM cost_basis_lots WHERE order_id = ?
    """, (order_id,))
    return cursor.fetchone()[0] > 0
