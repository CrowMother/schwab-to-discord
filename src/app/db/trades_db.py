from __future__ import annotations

import os
import sqlite3
from typing import Optional


def _ensure_parent_dir(db_path: str) -> None:
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _apply_pragmas(conn: sqlite3.Connection) -> None:
    # Keep it sane + fast for a small bot
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")


def init_trades_db(db_path: str, conn: Optional[sqlite3.Connection] = None) -> None:
    """
    Creates the `trades` table and related indexes.
    If conn is provided, uses it and does not close it.
    """
    _ensure_parent_dir(db_path)

    should_close = conn is None
    if conn is None:
        conn = sqlite3.connect(db_path)
    try:
        _apply_pragmas(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
              trade_id TEXT PRIMARY KEY,

              source TEXT NOT NULL DEFAULT 'schwab',
              account_id TEXT,

              order_id TEXT,
              leg_id TEXT,
              execution_id TEXT,

              symbol TEXT NOT NULL,
              asset_type TEXT NOT NULL,
              side TEXT NOT NULL,

              quantity REAL NOT NULL,
              price REAL,
              status TEXT,

              exp_date TEXT,
              strike REAL,
              call_put TEXT,

              event_time TEXT NOT NULL,
              ingested_at TEXT NOT NULL,

              position_effect TEXT
            );
            """
        )

        # Dedupe helper: you can safely insert repeatedly
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_trades_source_keys
              ON trades(source, account_id, order_id, leg_id, execution_id);
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_trades_symbol_time
              ON trades(symbol, event_time);
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_trades_order
              ON trades(order_id, leg_id);
            """
        )

        conn.commit()
    finally:
        if should_close:
            conn.close()
