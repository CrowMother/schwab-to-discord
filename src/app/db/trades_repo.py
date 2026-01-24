from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_trade_id(trade) -> str:
    return (
        "schwab-fill:"
        f"{trade.account_number}|{trade.instrument_id}|{trade.order_id}|"
        f"{trade.leg_id or ''}|{trade.execution_time}|"
        f"{trade.fill_quantity}|{trade.fill_price or ''}"
    )



def store_trade_fill(conn: sqlite3.Connection, trade) -> str:
    """
    Store ONE fill-level trade event into `trades`.
    Idempotent via UNIQUE index.
    """
    trade_id = make_trade_id(trade)

    conn.execute(
        """
        INSERT OR IGNORE INTO trades (
          trade_id,
          account_number, instrument_id,
          order_id, leg_id, execution_time,
          symbol, asset_type, instruction, position_effect,
          fill_quantity, fill_price,
          status, description, entered_time, close_time,
          posted, posted_at, discord_message_id,
          ingested_at
        )
        VALUES (?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                0, NULL, NULL,
                ?);
        """,
        (
            trade_id,
            trade.account_number,
            trade.instrument_id,
            trade.order_id,
            trade.leg_id,
            trade.execution_time,
            trade.symbol,
            trade.asset_type,
            trade.instruction,
            getattr(trade, "position_effect", None),
            trade.fill_quantity,
            getattr(trade, "fill_price", None),
            getattr(trade, "status", None),
            getattr(trade, "description", None),
            getattr(trade, "entered_time", None),
            getattr(trade, "close_time", None),
            _now_iso(),
        ),
    )

    return trade_id


def update_position_state(conn: sqlite3.Connection, trade_id: str, trade) -> None:
    """
    Foundation position tracking:
      OPENING  -> +fill_quantity
      CLOSING  -> -fill_quantity

    NOTE: This assumes "long opens add, closes subtract".
    If you later support short options, you’ll refine this using instruction (STO/BTC).
    """
    pe = getattr(trade, "position_effect", None)
    if pe == "OPENING":
        delta = float(trade.fill_quantity)
    elif pe == "CLOSING":
        delta = -float(trade.fill_quantity)
    else:
        delta = 0.0  # unknown / not implemented yet

    conn.execute(
        """
        INSERT INTO trade_state (
          account_number, instrument_id,
          symbol, open_qty,
          last_trade_id, last_event_time,
          updated_at
        )
        VALUES (?, ?, ?, ?,
                ?, ?,
                ?)
        ON CONFLICT(account_number, instrument_id) DO UPDATE SET
          symbol = COALESCE(excluded.symbol, trade_state.symbol),
          open_qty = trade_state.open_qty + excluded.open_qty,
          last_trade_id = excluded.last_trade_id,
          last_event_time = excluded.last_event_time,
          updated_at = excluded.updated_at;
        """,
        (
            trade.account_number,
            trade.instrument_id,
            getattr(trade, "symbol", None),
            delta,
            trade_id,
            trade.execution_time,
            _now_iso(),
        ),
    )


def fetch_unposted_fills(conn: sqlite3.Connection, limit: int = 200):
    return conn.execute(
        """
        SELECT
          trade_id,
          symbol, instruction, asset_type, position_effect,
          fill_quantity, fill_price,
          status, description,
          execution_time,
          account_number, instrument_id,
          order_id, leg_id
        FROM trades
        WHERE posted = 0
        ORDER BY execution_time ASC
        LIMIT ?;
        """,
        (limit,),
    ).fetchall()


def mark_posted(conn: sqlite3.Connection, trade_id: str, discord_message_id: Optional[str] = None) -> None:
    conn.execute(
        """
        UPDATE trades
        SET posted = 1,
            posted_at = ?,
            discord_message_id = COALESCE(?, discord_message_id)
        WHERE trade_id = ?;
        """,
        (_now_iso(), discord_message_id, trade_id),
    )
