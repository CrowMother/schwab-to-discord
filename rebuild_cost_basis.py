#!/usr/bin/env python3
"""
Cost Basis Rebuild Script

Rebuilds the cost_basis_lots and lot_matches tables by processing
all trades in CHRONOLOGICAL order. This fixes issues caused by
out-of-order historical imports.

Usage:
    python rebuild_cost_basis.py [--dry-run]
"""

import argparse
import sqlite3
import os
from datetime import datetime, timezone
from dotenv import load_dotenv


def load_config():
    """Load configuration."""
    if os.path.exists("config/.env.secrets"):
        load_dotenv("config/.env.secrets")
        load_dotenv("config/schwab-to-discord.env")
    elif os.path.exists(".env"):
        load_dotenv(".env")

    db_path = os.environ.get("DB_PATH", "data/trades.db")
    if db_path.startswith("/data/") and os.path.exists("data/trades.db"):
        db_path = "data/trades.db"

    return db_path


def backup_tables(conn):
    """Backup existing cost basis tables."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Backup cost_basis_lots
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS cost_basis_lots_backup_{timestamp} AS
        SELECT * FROM cost_basis_lots
    """)

    # Backup lot_matches
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS lot_matches_backup_{timestamp} AS
        SELECT * FROM lot_matches
    """)

    # Backup unmatched_sells
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS unmatched_sells_backup_{timestamp} AS
        SELECT * FROM unmatched_sells
    """)

    conn.commit()
    print(f"Backed up tables with timestamp: {timestamp}")
    return timestamp


def clear_cost_basis_tables(conn):
    """Clear all cost basis tracking data."""
    conn.execute("DELETE FROM lot_matches")
    conn.execute("DELETE FROM unmatched_sells")
    conn.execute("DELETE FROM cost_basis_lots")
    conn.commit()
    print("Cleared cost basis tables")


def get_all_trades_chronological(conn):
    """Get all trades ordered by entered_time."""
    cursor = conn.execute("""
        SELECT order_id, symbol, underlying, instruction,
               filled_quantity, price, entered_time
        FROM trades
        WHERE instruction IS NOT NULL
        ORDER BY entered_time ASC
    """)
    return cursor.fetchall()


def extract_underlying(symbol):
    """Extract underlying from option symbol."""
    return symbol.split()[0] if " " in symbol else symbol


def process_buy(conn, order_id, symbol, quantity, price, entered_time):
    """Process a BUY order - create cost basis lot."""
    # Check if already exists
    cursor = conn.execute(
        "SELECT lot_id FROM cost_basis_lots WHERE order_id = ?",
        (order_id,)
    )
    if cursor.fetchone():
        return False  # Already exists

    underlying = extract_underlying(symbol)
    now = datetime.now(timezone.utc).isoformat()

    conn.execute("""
        INSERT INTO cost_basis_lots
        (order_id, symbol, underlying, quantity, remaining_qty, avg_cost, entered_time, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (order_id, symbol, underlying, quantity, quantity, price, entered_time, now))

    return True


def process_sell(conn, order_id, symbol, quantity, sell_price):
    """Process a SELL order - LIFO match against lots."""
    # Check if already matched
    cursor = conn.execute(
        "SELECT COUNT(*) FROM lot_matches WHERE sell_order_id = ?",
        (order_id,)
    )
    if cursor.fetchone()[0] > 0:
        return None  # Already matched

    # Check if recorded as unmatched
    cursor = conn.execute(
        "SELECT COUNT(*) FROM unmatched_sells WHERE sell_order_id = ?",
        (order_id,)
    )
    if cursor.fetchone()[0] > 0:
        return None  # Already recorded as unmatched

    # Get open lots in LIFO order (newest first)
    cursor = conn.execute("""
        SELECT lot_id, order_id, symbol, quantity, remaining_qty, avg_cost, entered_time
        FROM cost_basis_lots
        WHERE symbol = ? AND remaining_qty > 0
        ORDER BY entered_time DESC
    """, (symbol,))
    lots = cursor.fetchall()

    if not lots:
        # No lots to match - record as unmatched
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("""
            INSERT OR IGNORE INTO unmatched_sells
            (sell_order_id, symbol, quantity, sell_price, recorded_at)
            VALUES (?, ?, ?, ?, ?)
        """, (order_id, symbol, quantity, sell_price, now))
        return None

    remaining_to_sell = quantity
    total_weighted_gain = 0.0
    total_qty_matched = 0.0
    now = datetime.now(timezone.utc).isoformat()

    for lot in lots:
        if remaining_to_sell <= 0:
            break

        lot_id, _, _, lot_qty, lot_remaining, lot_cost, _ = lot
        qty_from_lot = min(remaining_to_sell, lot_remaining)

        # Calculate gain
        if lot_cost > 0:
            gain_pct = ((sell_price - lot_cost) / lot_cost) * 100
        else:
            gain_pct = 0.0

        gain_amount = (sell_price - lot_cost) * qty_from_lot * 100  # Options multiplier

        # Record match
        conn.execute("""
            INSERT INTO lot_matches
            (sell_order_id, lot_id, quantity, cost_basis, sell_price, gain_pct, gain_amount, matched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (order_id, lot_id, qty_from_lot, lot_cost, sell_price, gain_pct, gain_amount, now))

        # Reduce lot
        conn.execute("""
            UPDATE cost_basis_lots
            SET remaining_qty = remaining_qty - ?
            WHERE lot_id = ?
        """, (qty_from_lot, lot_id))

        total_weighted_gain += gain_pct * qty_from_lot
        total_qty_matched += qty_from_lot
        remaining_to_sell -= qty_from_lot

    if total_qty_matched > 0:
        return total_weighted_gain / total_qty_matched
    return None


def rebuild_cost_basis(conn, dry_run=False):
    """Rebuild all cost basis data in chronological order."""
    trades = get_all_trades_chronological(conn)

    print(f"Found {len(trades)} trades to process")

    buys_processed = 0
    sells_processed = 0
    sells_matched = 0
    sells_unmatched = 0

    for trade in trades:
        order_id, symbol, underlying, instruction, qty, price, entered_time = trade
        instruction = instruction.upper() if instruction else ""

        if "BUY" in instruction:
            if not dry_run:
                if process_buy(conn, order_id, symbol, qty, price, entered_time):
                    buys_processed += 1
            else:
                buys_processed += 1

        elif "SELL" in instruction:
            if not dry_run:
                result = process_sell(conn, order_id, symbol, qty, price)
                sells_processed += 1
                if result is not None:
                    sells_matched += 1
                else:
                    # Check if it was unmatched or already processed
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM unmatched_sells WHERE sell_order_id = ?",
                        (order_id,)
                    )
                    if cursor.fetchone()[0] > 0:
                        sells_unmatched += 1
            else:
                sells_processed += 1

    if not dry_run:
        conn.commit()

    print(f"\nResults:")
    print(f"  BUY orders processed: {buys_processed}")
    print(f"  SELL orders processed: {sells_processed}")
    if not dry_run:
        print(f"  SELL orders matched: {sells_matched}")
        print(f"  SELL orders unmatched: {sells_unmatched}")


def verify_googl_325c(conn):
    """Verify GOOGL 325c cost basis is correct."""
    print("\n=== Verification: GOOGL 325c ===")

    # Check the specific sell we were debugging
    cursor = conn.execute("""
        SELECT lm.lot_id, lm.quantity, lm.cost_basis, lm.sell_price, lm.gain_pct,
               cb.entered_time as lot_time
        FROM lot_matches lm
        JOIN cost_basis_lots cb ON cb.lot_id = lm.lot_id
        WHERE lm.sell_order_id = 1005418020522
    """)

    for row in cursor.fetchall():
        print(f"  Sell matched Lot #{row[0]}: cost=${row[2]:.2f} -> sell=${row[3]:.2f} = {row[4]:.2f}%")
        print(f"    Lot entered_time: {row[5]}")

    # Expected: Should match the $1.84 lot (16:54), not the $1.38 lot (15:31)
    # Correct gain: (2.07 - 1.84) / 1.84 = 12.5%


def main():
    parser = argparse.ArgumentParser(description="Rebuild cost basis data in chronological order")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without making changes")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup (not recommended)")
    args = parser.parse_args()

    db_path = load_config()
    print(f"Using database: {db_path}")

    conn = sqlite3.connect(db_path)

    try:
        if args.dry_run:
            print("\n[DRY RUN] - No changes will be made\n")
            rebuild_cost_basis(conn, dry_run=True)
        else:
            # Backup first
            if not args.no_backup:
                backup_tables(conn)

            # Clear existing data
            clear_cost_basis_tables(conn)

            # Rebuild in chronological order
            rebuild_cost_basis(conn, dry_run=False)

            # Verify
            verify_googl_325c(conn)

            print("\nCost basis rebuild complete!")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
