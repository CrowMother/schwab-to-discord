#!/usr/bin/env python3
"""Export completed trades to Google Sheets.

Exports trades with FIFO matching data to a Google Sheet in the format:
Posted Date | Ticker | Exp. | Contract | Entry | Max Exit | % | Win/Loss | SIZING
"""

import os
import sqlite3
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from app.cost_basis import parse_strike_display, parse_expiration
from app.gsheet import connect_to_sheet, append_rows, get_existing_entries

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Configuration from environment
DB_PATH = os.environ.get("DB_PATH", "/data/trades.db")
CREDENTIALS_PATH = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_PATH", "/data/credentials.json")
SPREADSHEET_ID = os.environ.get(
    "GOOGLE_SHEETS_SPREADSHEET_ID",
    "14DKgxt8RbQdGxLiircSCLuA0Yxh-LDDlbZYEOMMO6eA"
)
WORKSHEET_NAME = os.environ.get("GOOGLE_SHEETS_WORKSHEET_NAME", "Sheet1")


def get_month_date_range(year: int, month: int):
    """Get start and end date strings for a given month."""
    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{month + 1:02d}-01"
    return start, end


def format_date_mmdd(date_str: str) -> str:
    """Convert ISO date string to MM/DD format."""
    if not date_str:
        return ""
    try:
        # Handle ISO format: 2025-06-09T14:30:00+0000
        dt = datetime.fromisoformat(date_str.replace("+0000", "+00:00").replace("Z", "+00:00"))
        return dt.strftime("%m/%d")
    except (ValueError, AttributeError):
        # Try simpler format
        try:
            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
            return dt.strftime("%m/%d")
        except (ValueError, AttributeError):
            return date_str[:5] if date_str else ""


def get_win_loss(gain_pct: float) -> str:
    """Determine WIN/LOSS/BREAK EVEN from gain percentage."""
    if gain_pct is None:
        return ""
    if gain_pct > 0.5:  # Small threshold for break even
        return "WIN"
    elif gain_pct < -0.5:
        return "LOSS"
    else:
        return "BREAK EVEN"


def format_percentage(gain_pct: float) -> str:
    """Format gain percentage for display."""
    if gain_pct is None:
        return ""
    return f"{gain_pct:.2f}%"


def get_completed_trades(conn: sqlite3.Connection, year: int = None, month: int = None, start_date: str = None, end_date: str = None) -> list:
    """
    Get completed trades (with FIFO matches) from database.

    Args:
        conn: SQLite connection
        year, month: Optional month filter
        start_date, end_date: Optional date range filter (ISO format YYYY-MM-DD)

    Returns list of dicts with: close_time, description, underlying, entry, exit, gain_pct
    """
    if start_date and end_date:
        # Use explicit date range
        cursor = conn.execute("""
            SELECT
                t.close_time,
                t.description,
                c.underlying,
                m.cost_basis AS entry,
                m.sell_price AS exit_price,
                m.gain_pct
            FROM lot_matches m
            JOIN trades t ON t.order_id = m.sell_order_id
            JOIN cost_basis_lots c ON c.lot_id = m.lot_id
            WHERE t.close_time >= ? AND t.close_time < ?
            ORDER BY t.close_time ASC
        """, (start_date, end_date))
    elif year and month:
        start, end = get_month_date_range(year, month)
        cursor = conn.execute("""
            SELECT
                t.close_time,
                t.description,
                c.underlying,
                m.cost_basis AS entry,
                m.sell_price AS exit_price,
                m.gain_pct
            FROM lot_matches m
            JOIN trades t ON t.order_id = m.sell_order_id
            JOIN cost_basis_lots c ON c.lot_id = m.lot_id
            WHERE t.close_time >= ? AND t.close_time < ?
            ORDER BY t.close_time ASC
        """, (start, end))
    else:
        cursor = conn.execute("""
            SELECT
                t.close_time,
                t.description,
                c.underlying,
                m.cost_basis AS entry,
                m.sell_price AS exit_price,
                m.gain_pct
            FROM lot_matches m
            JOIN trades t ON t.order_id = m.sell_order_id
            JOIN cost_basis_lots c ON c.lot_id = m.lot_id
            ORDER BY t.close_time ASC
        """)

    trades = []
    for row in cursor.fetchall():
        close_time, description, underlying, entry, exit_price, gain_pct = row
        trades.append({
            "close_time": close_time,
            "description": description,
            "underlying": underlying,
            "entry": entry,
            "exit": exit_price,
            "gain_pct": gain_pct,
        })

    return trades


def format_trade_row(trade: dict) -> list:
    """
    Format a trade dict into a row for Google Sheets.

    Columns: Posted Date | Ticker | Exp. | Contract | Entry | Max Exit | % | Win/Loss | SIZING
    """
    description = trade.get("description", "")

    return [
        format_date_mmdd(trade.get("close_time", "")),  # Posted Date (MM/DD)
        trade.get("underlying", ""),                     # Ticker
        parse_expiration(description),                   # Exp.
        parse_strike_display(description),               # Contract (e.g., "84c")
        trade.get("entry", ""),                          # Entry
        trade.get("exit", ""),                           # Max Exit / Stop Price
        format_percentage(trade.get("gain_pct")),        # Max Exit / Stop Price Percentage
        get_win_loss(trade.get("gain_pct")),            # Win / Loss
        "",                                              # SIZING (left blank)
    ]


def export_to_gsheet(year: int = None, month: int = None):
    """Export trades to Google Sheets."""
    # Default to current month
    if year is None or month is None:
        now = datetime.now()
        year, month = now.year, now.month

    month_name = datetime(year, month, 1).strftime("%B %Y")

    print(f"=" * 60)
    print(f"GOOGLE SHEETS EXPORT: {month_name}")
    print(f"=" * 60)

    # Connect to database
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    # Get completed trades
    trades = get_completed_trades(conn, year, month)
    conn.close()

    if not trades:
        print(f"No completed trades found for {month_name}")
        return

    print(f"Found {len(trades)} completed trades")

    # Connect to Google Sheets
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"ERROR: Credentials file not found at {CREDENTIALS_PATH}")
        print("Please add your Google service account JSON to ./data/credentials.json")
        return

    try:
        worksheet = connect_to_sheet(CREDENTIALS_PATH, SPREADSHEET_ID, WORKSHEET_NAME)
    except Exception as e:
        print(f"ERROR: Could not connect to Google Sheets: {e}")
        return

    # Get existing entries to avoid duplicates
    existing = get_existing_entries(worksheet)
    print(f"Found {len(existing)} existing entries in sheet")

    # Format rows and filter duplicates
    new_rows = []
    skipped = 0

    for trade in trades:
        row = format_trade_row(trade)
        # Check for duplicate: (Posted Date, Ticker, Contract)
        key = (row[0], row[1], row[3])
        if key in existing:
            skipped += 1
            continue
        new_rows.append(row)

    if not new_rows:
        print(f"No new trades to add (skipped {skipped} duplicates)")
        return

    # Append to sheet
    try:
        count = append_rows(worksheet, new_rows)
        print(f"Successfully added {count} new trades to Google Sheets")
        if skipped:
            print(f"Skipped {skipped} duplicates")
    except Exception as e:
        print(f"ERROR: Could not append rows: {e}")
        return

    # Summary
    wins = sum(1 for r in new_rows if r[7] == "WIN")
    losses = sum(1 for r in new_rows if r[7] == "LOSS")
    print(f"=" * 60)
    print(f"Summary: {wins} wins, {losses} losses")
    print(f"Spreadsheet: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    print(f"=" * 60)


def export_weekly():
    """Export trades from the last 7 days to Google Sheets.

    This is called by the scheduler every week.
    """
    from datetime import timedelta

    now = datetime.now()
    end_date = now.strftime("%Y-%m-%d")
    start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")

    logger.info(f"Weekly export: {start_date} to {end_date}")
    print(f"=" * 60)
    print(f"WEEKLY GOOGLE SHEETS EXPORT: {start_date} to {end_date}")
    print(f"=" * 60)

    # Connect to database
    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found at {DB_PATH}")
        return 0

    conn = sqlite3.connect(DB_PATH)

    # Get completed trades for the last 7 days
    trades = get_completed_trades(conn, start_date=start_date, end_date=end_date + "T23:59:59")
    conn.close()

    if not trades:
        logger.info(f"No completed trades found for {start_date} to {end_date}")
        return 0

    logger.info(f"Found {len(trades)} completed trades")

    # Connect to Google Sheets
    if not os.path.exists(CREDENTIALS_PATH):
        logger.error(f"Credentials file not found at {CREDENTIALS_PATH}")
        return 0

    try:
        worksheet = connect_to_sheet(CREDENTIALS_PATH, SPREADSHEET_ID, WORKSHEET_NAME)
    except Exception as e:
        logger.error(f"Could not connect to Google Sheets: {e}")
        return 0

    # Get existing entries to avoid duplicates
    existing = get_existing_entries(worksheet)
    logger.info(f"Found {len(existing)} existing entries in sheet")

    # Format rows and filter duplicates
    new_rows = []
    skipped = 0

    for trade in trades:
        row = format_trade_row(trade)
        # Check for duplicate: (Posted Date, Ticker, Contract)
        key = (row[0], row[1], row[3])
        if key in existing:
            skipped += 1
            continue
        new_rows.append(row)

    if not new_rows:
        logger.info(f"No new trades to add (skipped {skipped} duplicates)")
        return 0

    # Append to sheet
    try:
        count = append_rows(worksheet, new_rows)
        logger.info(f"Successfully added {count} new trades to Google Sheets")
        if skipped:
            logger.info(f"Skipped {skipped} duplicates")
        return count
    except Exception as e:
        logger.error(f"Could not append rows: {e}")
        return 0


if __name__ == "__main__":
    import sys

    # Allow passing year and month as arguments: python export_to_gsheet.py 2025 06
    if len(sys.argv) >= 3:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
        export_to_gsheet(year, month)
    elif len(sys.argv) == 2 and sys.argv[1] == "weekly":
        # Run weekly export
        export_weekly()
    else:
        # Default to current month
        export_to_gsheet()
