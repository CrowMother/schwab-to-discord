from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_trade_id(order_id: int) -> str:
    # deterministic, stable, tied to Schwab order id
    return f"schwab-order:{order_id}"


def store_trade(conn: sqlite3.Connection, trade) -> str:
    """
    Stores the trade dataclass into `trades` (raw, no cleaning).
    `trade` is your existing Trade dataclass instance.
    Returns trade_id.
    """
    trade_id = make_trade_id(trade.order_id)

    conn.execute(
        """
        INSERT INTO trades (
        trade_id,
        order_id, symbol, asset_type, instruction, description,
        quantity, filled_quantity, remaining_quantity,
        price, status,
        entered_time, close_time,
        ingested_at
        )
        VALUES (?, ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?)
        ON CONFLICT(order_id) DO UPDATE SET
        symbol = excluded.symbol,
        asset_type = excluded.asset_type,
        instruction = excluded.instruction,
        description = excluded.description,
        quantity = excluded.quantity,
        filled_quantity = excluded.filled_quantity,
        remaining_quantity = excluded.remaining_quantity,
        price = excluded.price,
        status = excluded.status,
        entered_time = excluded.entered_time,
        close_time = excluded.close_time,
        ingested_at = excluded.ingested_at;
        """,
        (
            trade_id,
            trade.order_id,
            trade.symbol,
            trade.asset_type,
            trade.instruction,
            trade.description,          # now matches a column
            trade.quantity,
            trade.filled_quantity,
            trade.remaining_quantity,
            trade.price,
            trade.status,
            trade.entered_time,
            trade.close_time,
            _now_iso(),
        ),
    )


    return trade_id


def ensure_trade_state(conn: sqlite3.Connection, trade_id: str) -> None:
    """
    Creates state row if missing. Leaves future fields NULL.
    """
    conn.execute(
        """
        INSERT OR IGNORE INTO trade_state (
          trade_id, posted, posted_at, discord_message_id, open_qty, updated_at
        )
        VALUES (?, 0, NULL, NULL, NULL, ?);
        """,
        (trade_id, _now_iso()),
    )


def mark_posted(conn: sqlite3.Connection, trade_id: str, discord_message_id: Optional[str] = None) -> None:
    conn.execute(
        """
        UPDATE trade_state
        SET posted = 1,
            posted_at = COALESCE(posted_at, ?),
            discord_message_id = COALESCE(?, discord_message_id),
            updated_at = ?
        WHERE trade_id = ?;
        """,
        (_now_iso(), discord_message_id, _now_iso(), trade_id),
    )
