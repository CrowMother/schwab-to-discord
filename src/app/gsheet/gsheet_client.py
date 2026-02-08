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
