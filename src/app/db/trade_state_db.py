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


def init_trade_state_db(db_path: str, conn: Optional[sqlite3.Connection] = None) -> None:
    _ensure_parent_dir(db_path)

    should_close = conn is None
    if conn is None:
        conn = sqlite3.connect(db_path)

    try:
        _apply_pragmas(conn)

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_state (
              account_number TEXT NOT NULL,
              instrument_id INTEGER NOT NULL,

              symbol TEXT,
              open_qty REAL NOT NULL DEFAULT 0,

              last_trade_id TEXT,
              last_event_time TEXT,

              updated_at TEXT NOT NULL,

              PRIMARY KEY (account_number, instrument_id)
            );
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_trade_state_open_qty
              ON trade_state(open_qty);
            """
        )

        conn.commit()
    finally:
        if should_close:
            conn.close()
