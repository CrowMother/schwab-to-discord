# src/app/db/trades_db.py
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

    


def _add_column_if_missing(conn: sqlite3.Connection, table_name: str, column_name: str, column_type: str) -> None:
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


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

              -- trade dataclass fields (raw, columnized)
              order_id INTEGER NOT NULL,
              symbol TEXT NOT NULL,
              asset_type TEXT NOT NULL,
              instruction TEXT NOT NULL,

               description TEXT,            -- NEW

              quantity REAL NOT NULL,
              filled_quantity REAL NOT NULL,
              remaining_quantity REAL NOT NULL,

              price REAL,
              status TEXT NOT NULL,

              entered_time TEXT NOT NULL,
              close_time TEXT,

              ingested_at TEXT NOT NULL
            );
            """
        )

        # Dedupe: one order_id row for now (simple foundation)
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_trades_order_id
              ON trades(order_id);
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_trades_symbol_entered
              ON trades(symbol, entered_time);
            """
        )
        _add_column_if_missing(conn, "trades", "description", "TEXT")
        _add_column_if_missing(conn, "trades", "underlying", "TEXT")

        conn.commit()
    finally:
        if should_close:
            conn.close()
