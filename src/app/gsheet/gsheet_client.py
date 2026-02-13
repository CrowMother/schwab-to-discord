# src/app/gsheet/gsheet_client.py
"""Google Sheets client for exporting trades."""

from __future__ import annotations

import logging
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def connect_to_sheet(
    credentials_path: str, spreadsheet_id: str, worksheet_name: str = "Sheet1"
) -> gspread.Worksheet:
    """
    Connect to a Google Sheet using service account credentials.

    Args:
        credentials_path: Path to service account JSON file
        spreadsheet_id: The spreadsheet ID from the URL
        worksheet_name: Name of the worksheet (default: Sheet1)

    Returns:
        gspread.Worksheet object
    """
    credentials = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)

    logger.info(f"Connected to spreadsheet: {spreadsheet.title}")
    return worksheet


def get_existing_entries(worksheet: gspread.Worksheet) -> set:
    """
    Get existing entries to avoid duplicates.

    Returns a set of (date, ticker, contract) tuples.
    """
    try:
        records = worksheet.get_all_values()
        existing = set()

        # Skip header row
        for row in records[1:]:
            if len(row) >= 4:
                # (Posted Date, Ticker, Contract) as unique key
                key = (row[0], row[1], row[3])
                existing.add(key)

        return existing
    except Exception as e:
        logger.warning(f"Could not fetch existing entries: {e}")
        return set()


def append_rows(worksheet: gspread.Worksheet, rows: list[list]) -> int:
    """
    Append rows to the worksheet.

    Args:
        worksheet: The worksheet to append to
        rows: List of rows, each row is a list of values

    Returns:
        Number of rows appended
    """
    if not rows:
        logger.info("No rows to append")
        return 0

    worksheet.append_rows(rows, value_input_option="USER_ENTERED")
    logger.info(f"Appended {len(rows)} rows to sheet")
    return len(rows)


def sort_sheet_by_date(worksheet: gspread.Worksheet, start_row: int = 2) -> None:
    """
    Sort the worksheet by the Posted Date column (column A).

    Args:
        worksheet: The worksheet to sort
        start_row: First data row (after header), default 2
    """
    try:
        # Get sheet dimensions
        all_values = worksheet.get_all_values()
        if len(all_values) <= 1:
            logger.info("No data to sort")
            return

        # Sort range: A2 to last column/row
        last_row = len(all_values)
        last_col = len(all_values[0]) if all_values else 9

        # Use gspread's sort method
        worksheet.sort((1, 'asc'), range=f'A{start_row}:I{last_row}')
        logger.info(f"Sorted {last_row - start_row + 1} rows by date")
    except Exception as e:
        logger.error(f"Could not sort sheet: {e}")


def get_or_create_stats_sheet(
    credentials_path: str, spreadsheet_id: str, stats_sheet_name: str = "Stats"
) -> gspread.Worksheet:
    """
    Get or create the Stats sheet tab.

    Args:
        credentials_path: Path to service account JSON file
        spreadsheet_id: The spreadsheet ID from the URL
        stats_sheet_name: Name of the stats worksheet (default: Stats)

    Returns:
        gspread.Worksheet object for the Stats sheet
    """
    credentials = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(spreadsheet_id)

    try:
        # Try to get existing Stats sheet
        stats_sheet = spreadsheet.worksheet(stats_sheet_name)
        logger.info(f"Found existing '{stats_sheet_name}' sheet")
    except gspread.WorksheetNotFound:
        # Create new Stats sheet
        stats_sheet = spreadsheet.add_worksheet(title=stats_sheet_name, rows=10, cols=2)
        # Add headers
        stats_sheet.update('A1:B3', [
            ['Metric', 'Value'],
            ['Win Rate', ''],
            ['Last Updated', '']
        ])
        logger.info(f"Created new '{stats_sheet_name}' sheet")

    return stats_sheet


def calculate_win_rate(worksheet: gspread.Worksheet) -> dict:
    """
    Calculate win/loss statistics from the Win/Loss column (H).

    Args:
        worksheet: The main data worksheet (Sheet1)

    Returns:
        Dict with wins, losses, total, and win_rate_pct
    """
    try:
        # Get all values from Win/Loss column (column H = index 7)
        all_values = worksheet.get_all_values()

        wins = 0
        losses = 0

        # Skip header row, read column H (index 7)
        for row in all_values[1:]:
            if len(row) >= 8:
                win_loss = row[7].strip().upper()
                if win_loss == "WIN":
                    wins += 1
                elif win_loss == "LOSS":
                    losses += 1
                # Ignore "BREAK EVEN" and empty values

        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0.0

        logger.info(f"Win rate calculated: {wins}W / {losses}L = {win_rate:.1f}%")

        return {
            "wins": wins,
            "losses": losses,
            "total": total,
            "win_rate_pct": round(win_rate, 1)
        }
    except Exception as e:
        logger.error(f"Error calculating win rate: {e}")
        return {"wins": 0, "losses": 0, "total": 0, "win_rate_pct": 0.0}


def update_stats_sheet(
    credentials_path: str,
    spreadsheet_id: str,
    data_sheet_name: str = "Sheet1",
    stats_sheet_name: str = "Stats"
) -> dict:
    """
    Calculate win rate from data sheet and update the Stats sheet.

    Args:
        credentials_path: Path to service account JSON file
        spreadsheet_id: The spreadsheet ID from the URL
        data_sheet_name: Name of the data worksheet (default: Sheet1)
        stats_sheet_name: Name of the stats worksheet (default: Stats)

    Returns:
        Dict with stats that were written
    """
    from datetime import datetime

    try:
        # Connect to data sheet and calculate stats
        data_sheet = connect_to_sheet(credentials_path, spreadsheet_id, data_sheet_name)
        stats = calculate_win_rate(data_sheet)

        # Get or create stats sheet
        stats_sheet = get_or_create_stats_sheet(credentials_path, spreadsheet_id, stats_sheet_name)

        # Format the win rate
        win_rate_str = f"{stats['win_rate_pct']}%"
        last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Update stats sheet (B2 = win rate, B3 = last updated)
        stats_sheet.update('B2:B3', [[win_rate_str], [last_updated]])

        logger.info(f"Stats sheet updated: Win Rate = {win_rate_str}")

        return stats
    except Exception as e:
        logger.error(f"Error updating stats sheet: {e}", exc_info=True)
        return {"wins": 0, "losses": 0, "total": 0, "win_rate_pct": 0.0}
