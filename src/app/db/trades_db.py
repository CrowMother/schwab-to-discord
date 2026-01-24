from __future__ import annotations

import os
import sqlite3
from typing import Optional


def _ensure_parent_dir(db_path: str) -> None:
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _apply_pragmas(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")


def init_trades_db(db_path: str, conn: Optional[sqlite3.Connection] = None) -> None:
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

              -- matching key foundation
              account_number TEXT NOT NULL,
              instrument_id INTEGER NOT NULL,

              -- order/fill identity
              order_id INTEGER NOT NULL,
              leg_id INTEGER,
              execution_time TEXT NOT NULL,   -- from executionLegs[].time

              -- what it is
              symbol TEXT NOT NULL,
              asset_type TEXT NOT NULL,
              instruction TEXT NOT NULL,
              position_effect TEXT,           -- OPENING/CLOSING

              -- fill data
              fill_quantity REAL NOT NULL,
              fill_price REAL,

              -- context
              status TEXT,
              description TEXT,
              entered_time TEXT,
              close_time TEXT,

              -- bot state (so we don’t need a per-trade state table)
              posted INTEGER NOT NULL DEFAULT 0,
              posted_at TEXT,
              discord_message_id TEXT,

              ingested_at TEXT NOT NULL
            );
            """
        )

        # Prevent duplicates if you re-run ingestion
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_trades_fill_dedupe
              ON trades(account_number, instrument_id, order_id, leg_id, execution_time, fill_quantity, fill_price);
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_trades_match_key_time
              ON trades(account_number, instrument_id, execution_time);
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_trades_posted_time
              ON trades(posted, execution_time);
            """
        )

        conn.commit()
    finally:
        if should_close:
            conn.close()
