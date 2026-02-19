# export_to_gsheet.py
"""Weekly Google Sheets export for trade data.

IMPORTANT: This script follows the EXISTING format in the Google Sheet.
- Only APPENDS new trades at the bottom (no sorting/reordering)
- Matches the exact format of existing entries
- Updates the Stats sheet with win/loss percentage after export
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def parse_option_description(description: str) -> dict:
    """
    Parse option description like "APA CORP 04/17/2026 $30 Call" into components.

    Returns dict matching EXISTING sheet format:
    - expiration: "04/17/2026"
    - contract: "30c" or "30p" (lowercase, no space)
    """
    result = {
        'expiration': '',
        'strike': '',
        'option_type': '',
        'contract': ''
    }

    if not description:
        return result

    # Match expiration date pattern: MM/DD/YYYY
    exp_match = re.search(r'(\d{2}/\d{2}/\d{4})', description)
    if exp_match:
        result['expiration'] = exp_match.group(1)

    # Match strike price and option type: $XX Call or $XX Put
    strike_match = re.search(r'\$(\d+(?:\.\d+)?)\s+(Call|Put)', description, re.IGNORECASE)
    if strike_match:
        result['strike'] = strike_match.group(1)
        option_type = strike_match.group(2).lower()
        # Format: "30c" or "30p" (lowercase, no space) - matches existing sheet format
        result['option_type'] = 'c' if option_type == 'call' else 'p'
        result['contract'] = f"{result['strike']}{result['option_type']}"

    return result


def format_posted_date(iso_date: str) -> str:
    """
    Convert ISO date to "MM/DD" format matching EXISTING sheet format.

    Args:
        iso_date: ISO format like "2026-02-12T20:36:01+0000"

    Returns:
        String like "02/12" (NO spaces, NO year)
    """
    try:
        # Parse ISO format
        dt = datetime.fromisoformat(iso_date.replace('+0000', '+00:00'))
        # Format: MM/DD (no spaces, no year) - matches existing sheet
        return dt.strftime("%m/%d")
    except Exception as e:
        logger.warning(f"Could not parse date {iso_date}: {e}")
        return ""


def determine_outcome(gain_pct: float) -> str:
    """
    Determine WIN/LOSS/BREAK EVEN based on gain percentage.

    Uses same thresholds as existing sheet entries.
    """
    if gain_pct is None:
        return ""

    # Based on existing sheet data analysis:
    # - Positive gains > ~5% = WIN
    # - Negative gains < ~-5% = LOSS
    # - Small gains/losses = BREAK EVEN
    if gain_pct > 5.0:
        return "WIN"
    elif gain_pct < -5.0:
        return "LOSS"
    else:
        return "BREAK EVEN"


def get_weekly_trades(conn: sqlite3.Connection, days_back: int = 7) -> list[dict]:
    """
    Get SELL trades from the past N days with their cost basis info.

    Returns trades in CHRONOLOGICAL order (oldest first) for proper appending.
    """
    query = """
        SELECT
            t.order_id,
            t.underlying,
            t.description,
            t.close_time,
            t.price as sell_price,
            lm.cost_basis as entry_price,
            lm.gain_pct,
            lm.quantity
        FROM trades t
        INNER JOIN lot_matches lm ON t.order_id = lm.sell_order_id
        WHERE t.instruction LIKE '%SELL%'
            AND t.status = 'FILLED'
            AND t.close_time >= datetime('now', ?)
        ORDER BY t.close_time ASC
    """

    cursor = conn.execute(query, (f'-{days_back} days',))
    rows = cursor.fetchall()

    trades = []
    for row in rows:
        order_id, underlying, description, close_time, sell_price, entry_price, gain_pct, quantity = row

        # Skip if no cost basis match (can't calculate P/L)
        if entry_price is None:
            continue

        # Parse option details from description
        option_info = parse_option_description(description)

        # Format the data to MATCH EXISTING SHEET FORMAT
        trade = {
            'order_id': order_id,
            'close_time': close_time,  # Keep for sorting
            'posted_date': format_posted_date(close_time),  # MM/DD format
            'ticker': underlying or '',
            'expiration': option_info['expiration'],
            'contract': option_info['contract'],  # "30c" format
            'entry': f"{entry_price:.2f}" if entry_price else '',
            'exit': f"{sell_price:.2f}" if sell_price else '',
            'pnl_pct': f"{gain_pct:.2f}%" if gain_pct is not None else '',
            'outcome': determine_outcome(gain_pct) if gain_pct is not None else ''
        }
        trades.append(trade)

    return trades


def trade_to_row(trade: dict) -> list:
    """Convert trade dict to Google Sheet row format matching EXISTING layout."""
    return [
        trade['posted_date'],      # A: Posted Date (MM/DD)
        trade['ticker'],           # B: Ticker
        trade['expiration'],       # C: Exp.
        trade['contract'],         # D: Contract (30c format)
        trade['entry'],            # E: Entry
        trade['exit'],             # F: Max Exit / Stop Price
        trade['pnl_pct'],          # G: Max Exit / Stop Price Percentage
        trade['outcome'],          # H: Win / Loss
    ]


def get_existing_entries_extended(worksheet) -> set:
    """
    Get existing entries using a more robust key to avoid duplicates.

    Uses (date, ticker, contract, entry, exit) as key for better matching.
    """
    try:
        records = worksheet.get_all_values()
        existing = set()

        # Skip header rows (first 2 rows based on sheet structure)
        for row in records[2:]:
            if len(row) >= 6 and row[0]:  # Has date and enough columns
                # Key: (Posted Date, Ticker, Contract, Entry, Exit)
                key = (row[0], row[1], row[3], row[4], row[5])
                existing.add(key)

        return existing
    except Exception as e:
        logger.warning(f"Could not fetch existing entries: {e}")
        return set()


def export_weekly() -> int:
    """
    Export weekly trades to Google Sheets.

    - Only APPENDS new trades at the bottom
    - Does NOT sort or reorder existing data
    - Matches existing sheet format exactly
    - Updates Stats sheet after export

    Returns:
        Number of trades exported
    """
    try:
        import sys
        project_root = os.path.dirname(os.path.abspath(__file__))
        src_path = os.path.join(project_root, 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        from app.gsheet.gsheet_client import (
            connect_to_sheet,
            append_rows,
            update_stats_sheet
        )
    except ImportError as e:
        logger.error(f"Could not import gsheet_client: {e}")
        raise

    # Get config from environment
    credentials_path = os.environ.get(
        "GOOGLE_SHEETS_CREDENTIALS_PATH",
        "/data/dulcet-abacus-481722-g8-7d60a0bb5dd7.json"
    )
    spreadsheet_id = os.environ.get(
        "GOOGLE_SHEETS_SPREADSHEET_ID",
        "14DKgxt8RbQdGxLiircSCLuA0Yxh-LDDlbZYEOMMO6eA"
    )
    worksheet_name = os.environ.get(
        "GOOGLE_SHEETS_WORKSHEET_NAME",
        "Sheet1"
    )
    db_path = os.environ.get("DB_PATH", "/data/trades.db")

    logger.info(f"Starting weekly Google Sheets export")
    logger.info(f"  Database: {db_path}")
    logger.info(f"  Spreadsheet: {spreadsheet_id}")

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Get trades from the past week (in chronological order)
        trades = get_weekly_trades(conn, days_back=7)
        logger.info(f"Found {len(trades)} SELL trades from the past week")

        if not trades:
            logger.info("No new trades to export")
            return 0

        # Connect to Google Sheet
        worksheet = connect_to_sheet(credentials_path, spreadsheet_id, worksheet_name)

        # Get existing entries to avoid duplicates (using extended key)
        existing = get_existing_entries_extended(worksheet)
        logger.info(f"Found {len(existing)} existing entries in sheet")

        # Filter out duplicates - only add truly new trades
        new_rows = []
        for trade in trades:
            # Key: (Posted Date, Ticker, Contract, Entry, Exit)
            key = (
                trade['posted_date'],
                trade['ticker'],
                trade['contract'],
                trade['entry'],
                trade['exit']
            )
            if key not in existing:
                new_rows.append(trade_to_row(trade))
                existing.add(key)  # Prevent duplicates within this batch

        logger.info(f"After deduplication: {len(new_rows)} new trades to add")

        if not new_rows:
            logger.info("All trades already exist in sheet")
            return 0

        # ONLY APPEND at the bottom - do NOT sort
        count = append_rows(worksheet, new_rows)
        logger.info(f"Appended {count} new trades to bottom of sheet")

        # Update Stats sheet with win/loss percentage
        try:
            stats = update_stats_sheet(credentials_path, spreadsheet_id)
            logger.info(f"Stats updated: {stats['win_rate_pct']}% win rate")
        except Exception as e:
            logger.warning(f"Could not update stats sheet: {e}")

        logger.info(f"Successfully exported {count} trades to Google Sheets")
        return count

    finally:
        conn.close()


def export_all() -> int:
    """
    Export ALL unsynced trades to Google Sheets.

    Same as export_weekly but looks at all historical trades.
    Only adds trades that don't already exist in the sheet.
    """
    try:
        import sys
        project_root = os.path.dirname(os.path.abspath(__file__))
        src_path = os.path.join(project_root, 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        from app.gsheet.gsheet_client import (
            connect_to_sheet,
            append_rows,
            update_stats_sheet
        )
    except ImportError as e:
        logger.error(f"Could not import gsheet_client: {e}")
        raise

    # Get config from environment
    credentials_path = os.environ.get(
        "GOOGLE_SHEETS_CREDENTIALS_PATH",
        "/data/dulcet-abacus-481722-g8-7d60a0bb5dd7.json"
    )
    spreadsheet_id = os.environ.get(
        "GOOGLE_SHEETS_SPREADSHEET_ID",
        "14DKgxt8RbQdGxLiircSCLuA0Yxh-LDDlbZYEOMMO6eA"
    )
    worksheet_name = os.environ.get(
        "GOOGLE_SHEETS_WORKSHEET_NAME",
        "Sheet1"
    )
    db_path = os.environ.get("DB_PATH", "/data/trades.db")

    logger.info(f"Starting FULL Google Sheets export")

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Get ALL trades with cost basis (chronological order)
        query = """
            SELECT
                t.order_id,
                t.underlying,
                t.description,
                t.close_time,
                t.price as sell_price,
                lm.cost_basis as entry_price,
                lm.gain_pct,
                lm.quantity
            FROM trades t
            INNER JOIN lot_matches lm ON t.order_id = lm.sell_order_id
            WHERE t.instruction LIKE '%SELL%'
                AND t.status = 'FILLED'
            ORDER BY t.close_time ASC
        """
        cursor = conn.execute(query)
        rows = cursor.fetchall()

        trades = []
        for row in rows:
            order_id, underlying, description, close_time, sell_price, entry_price, gain_pct, quantity = row
            if entry_price is None:
                continue

            option_info = parse_option_description(description)
            trade = {
                'order_id': order_id,
                'posted_date': format_posted_date(close_time),
                'ticker': underlying or '',
                'expiration': option_info['expiration'],
                'contract': option_info['contract'],
                'entry': f"{entry_price:.2f}" if entry_price else '',
                'exit': f"{sell_price:.2f}" if sell_price else '',
                'pnl_pct': f"{gain_pct:.2f}%" if gain_pct is not None else '',
                'outcome': determine_outcome(gain_pct) if gain_pct is not None else ''
            }
            trades.append(trade)

        logger.info(f"Found {len(trades)} total SELL trades with cost basis")

        if not trades:
            return 0

        # Connect to Google Sheet
        worksheet = connect_to_sheet(credentials_path, spreadsheet_id, worksheet_name)
        existing = get_existing_entries_extended(worksheet)
        logger.info(f"Found {len(existing)} existing entries in sheet")

        # Filter duplicates
        new_rows = []
        for trade in trades:
            key = (
                trade['posted_date'],
                trade['ticker'],
                trade['contract'],
                trade['entry'],
                trade['exit']
            )
            if key not in existing:
                new_rows.append(trade_to_row(trade))
                existing.add(key)

        logger.info(f"After deduplication: {len(new_rows)} new trades to add")

        if not new_rows:
            logger.info("All trades already exist in sheet")
            return 0

        # Append at bottom only
        count = append_rows(worksheet, new_rows)

        # Update stats
        try:
            stats = update_stats_sheet(credentials_path, spreadsheet_id)
            logger.info(f"Stats updated: {stats['win_rate_pct']}% win rate")
        except Exception as e:
            logger.warning(f"Could not update stats sheet: {e}")

        return count

    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )

    import argparse
    parser = argparse.ArgumentParser(description="Export trades to Google Sheets")
    parser.add_argument('--all', action='store_true', help="Export ALL trades (not just weekly)")
    parser.add_argument('--db', default=None, help="Database path (overrides DB_PATH env var)")
    args = parser.parse_args()

    if args.db:
        os.environ['DB_PATH'] = args.db

    if args.all:
        count = export_all()
    else:
        count = export_weekly()

    print(f"Exported {count} trades")
