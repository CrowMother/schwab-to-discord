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
    """
    Creates the `trade_state` table and related indexes.
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
            CREATE TABLE IF NOT EXISTS trade_state (
              trade_id TEXT PRIMARY KEY REFERENCES trades(trade_id) ON DELETE CASCADE,

              posted INTEGER NOT NULL DEFAULT 0,
              posted_at TEXT,
              discord_message_id TEXT,

              open_qty REAL NOT NULL DEFAULT 0,
              updated_at TEXT NOT NULL
            );
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_trade_state_posted
              ON trade_state(posted, updated_at);
            """
        )

        conn.commit()
    finally:
        if should_close:
            conn.close()
