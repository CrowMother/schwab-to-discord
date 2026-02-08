#!/usr/bin/env python3
"""Export trades from SQLite to Excel file in data folder."""

import sqlite3
import os
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv()

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    print("Installing openpyxl...")
    import subprocess
    subprocess.check_call(["pip", "install", "openpyxl"])
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

import schwabdev

DB_PATH = os.environ.get("DB_PATH", "/data/trades.db")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/data")


def get_cost_basis_lots(conn):
    """Get all cost basis lots from database."""
    try:
        cursor = conn.execute("""
            SELECT lot_id, order_id, symbol, underlying, quantity, remaining_qty,
                   avg_cost, entered_time, created_at
            FROM cost_basis_lots
            ORDER BY entered_time DESC
        """)
        return cursor.fetchall()
    except sqlite3.OperationalError:
        return []


def get_lot_matches(conn):
    """Get all lot matches (sell order to lot mappings) from database."""
    try:
        cursor = conn.execute("""
            SELECT m.match_id, m.sell_order_id, m.lot_id, m.quantity,
                   m.cost_basis, m.sell_price, m.gain_pct, m.gain_amount, m.matched_at,
                   l.symbol, l.underlying
            FROM lot_matches m
            JOIN cost_basis_lots l ON m.lot_id = l.lot_id
            ORDER BY m.matched_at DESC
        """)
        return cursor.fetchall()
    except sqlite3.OperationalError:
        return []


def get_gain_for_trade(conn, order_id, instruction):
    """Get gain percentage for a sell trade."""
    if not instruction or "SELL" not in instruction.upper():
        return None
    try:
        cursor = conn.execute("""
            SELECT SUM(quantity * gain_pct) / SUM(quantity) as avg_gain
            FROM lot_matches
            WHERE sell_order_id = ?
        """, (order_id,))
        result = cursor.fetchone()
        return result[0] if result and result[0] is not None else None
    except sqlite3.OperationalError:
        return None

def get_schwab_positions():
    """Fetch current positions directly from Schwab account."""
    client = schwabdev.Client(
        app_key=os.getenv("SCHWAB_APP_KEY"),
        app_secret=os.getenv("SCHWAB_APP_SECRET"),
        callback_url=os.getenv("CALLBACK_URL"),
        tokens_db=os.getenv("TOKENS_DB", "/data/tokens.db"),
        timeout=int(os.getenv("SCHWAB_TIMEOUT", 10))
    )

    resp = client.account_details_all(fields="positions")
    resp.raise_for_status()
    accounts = resp.json()

    positions = []
    positions_by_symbol = {}

    for account in accounts:
        account_positions = account.get("securitiesAccount", {}).get("positions", [])
        for pos in account_positions:
            instrument = pos.get("instrument", {})
            asset_type = instrument.get("assetType", "N/A")
            # Only include options, skip equity
            if asset_type != "OPTION":
                continue

            symbol = instrument.get("symbol", "N/A")
            qty = pos.get("longQuantity", 0) - pos.get("shortQuantity", 0)

            positions.append({
                "symbol": symbol,
                "asset_type": asset_type,
                "quantity": qty,
                "avg_price": pos.get("averagePrice", 0),
                "market_value": pos.get("marketValue", 0),
            })

            # Build lookup by underlying symbol (first part before space)
            underlying = symbol.split()[0] if " " in symbol else symbol
            if underlying not in positions_by_symbol:
                positions_by_symbol[underlying] = 0
            positions_by_symbol[underlying] += qty

    return positions, positions_by_symbol

def export_trades():
    conn = sqlite3.connect(DB_PATH)

    # Get all trades (including order_id for gain lookup)
    cursor = conn.execute("""
        SELECT
            order_id,
            symbol,
            asset_type,
            instruction,
            quantity,
            filled_quantity,
            remaining_quantity,
            price,
            status,
            entered_time,
            close_time,
            description
        FROM trades
        ORDER BY entered_time DESC
    """)
    rows = cursor.fetchall()

    if not rows:
        print("No trades found in database.")
        conn.close()
        return

    # Get actual positions from Schwab
    schwab_positions, positions_by_symbol = get_schwab_positions()

    # Get cost basis data
    cost_basis_lots = get_cost_basis_lots(conn)
    lot_matches = get_lot_matches(conn)

    # Calculate P/L per trade and add position remaining
    trades_with_pl = []
    for row in rows:
        order_id, symbol, asset_type, instruction, quantity, filled_qty, remaining_qty, price, status, entered, closed, desc = row

        multiplier = 100 if asset_type in ("OPTION", "OPTIONS") else 1
        filled = filled_qty if filled_qty else quantity
        trade_value = (price or 0) * filled * multiplier

        if instruction and "SELL" in instruction.upper():
            pl = trade_value
        elif instruction and "BUY" in instruction.upper():
            pl = -trade_value
        else:
            pl = 0

        # Get actual position remaining from Schwab (by underlying symbol)
        underlying = symbol.split()[0] if " " in symbol else symbol
        position_remaining = positions_by_symbol.get(underlying, 0)

        # Get gain percentage for sell orders
        gain_pct = get_gain_for_trade(conn, order_id, instruction)

        trades_with_pl.append((symbol, asset_type, instruction, quantity, filled_qty,
                               position_remaining, price, status, entered, closed, desc, pl, gain_pct))

    conn.close()

    # Create workbook
    wb = openpyxl.Workbook()

    # Style settings
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )
    buy_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    sell_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    profit_font = Font(color="006400", bold=True)
    loss_font = Font(color="8B0000", bold=True)

    # ===== SHEET 1: All Trades =====
    ws = wb.active
    ws.title = "All Trades"

    headers = [
        "Symbol", "Asset Type", "Action", "Quantity", "Filled", "Position Left",
        "Price", "Status", "Entry Date", "Close Date", "Notes", "P/L ($)", "Gain %"
    ]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    total_pl = 0
    for row_idx, row in enumerate(trades_with_pl, 2):
        for col_idx, value in enumerate(row, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center")

            # Position Left column - highlight if > 0
            if col_idx == 6 and value and value > 0:
                cell.font = Font(bold=True, color="1F4E79")

            # P/L column
            if col_idx == 12:
                cell.number_format = "$#,##0.00"
                if value and value > 0:
                    cell.font = profit_font
                elif value and value < 0:
                    cell.font = loss_font

            # Gain % column
            if col_idx == 13 and value is not None:
                cell.number_format = "0.00%"
                cell.value = value / 100 if value else 0  # Convert to decimal for %
                if value and value > 0:
                    cell.font = profit_font
                elif value and value < 0:
                    cell.font = loss_font

        total_pl += row[11] if row[11] else 0

        action = row[2] if row[2] else ""
        if "BUY" in action.upper():
            for col in range(1, len(headers) + 1):
                if col not in (6, 12, 13):
                    ws.cell(row=row_idx, column=col).fill = buy_fill
        elif "SELL" in action.upper():
            for col in range(1, len(headers) + 1):
                if col not in (6, 12, 13):
                    ws.cell(row=row_idx, column=col).fill = sell_fill

    total_row = len(trades_with_pl) + 2
    ws.cell(row=total_row, column=11, value="TOTAL P/L:").font = Font(bold=True)
    ws.cell(row=total_row, column=11).alignment = Alignment(horizontal="right")
    total_cell = ws.cell(row=total_row, column=12, value=total_pl)
    total_cell.number_format = "$#,##0.00"
    total_cell.font = Font(bold=True, color="006400" if total_pl >= 0 else "8B0000")
    total_cell.border = thin_border

    for col in range(1, len(headers) + 1):
        max_length = len(headers[col-1])
        for row in range(2, len(rows) + 2):
            cell_value = ws.cell(row=row, column=col).value
            if cell_value:
                max_length = max(max_length, len(str(cell_value)))
        ws.column_dimensions[get_column_letter(col)].width = min(max_length + 2, 30)

    ws.freeze_panes = "A2"

    # ===== SHEET 2: Open Positions (from Schwab API) =====
    ws2 = wb.create_sheet("Open Positions")

    pos_headers = ["Symbol", "Asset Type", "Quantity", "Avg Price", "Market Value", "Status"]

    for col, header in enumerate(pos_headers, 1):
        cell = ws2.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    row_idx = 2
    total_qty = 0
    total_value = 0

    for pos in schwab_positions:
        ws2.cell(row=row_idx, column=1, value=pos["symbol"]).border = thin_border
        ws2.cell(row=row_idx, column=2, value=pos["asset_type"]).border = thin_border

        qty_cell = ws2.cell(row=row_idx, column=3, value=pos["quantity"])
        qty_cell.border = thin_border
        qty_cell.font = Font(bold=True)

        price_cell = ws2.cell(row=row_idx, column=4, value=pos["avg_price"])
        price_cell.border = thin_border
        price_cell.number_format = "$#,##0.00"

        val_cell = ws2.cell(row=row_idx, column=5, value=pos["market_value"])
        val_cell.border = thin_border
        val_cell.number_format = "$#,##0.00"

        status_cell = ws2.cell(row=row_idx, column=6, value="OPEN - TO SELL")
        status_cell.border = thin_border
        status_cell.fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
        status_cell.font = Font(bold=True)

        for col in range(1, 6):
            ws2.cell(row=row_idx, column=col).alignment = Alignment(horizontal="center")

        total_qty += pos["quantity"]
        total_value += pos["market_value"]
        row_idx += 1

    # Total row
    ws2.cell(row=row_idx + 1, column=2, value="TOTAL:").font = Font(bold=True)
    ws2.cell(row=row_idx + 1, column=2).alignment = Alignment(horizontal="right")

    ws2.cell(row=row_idx + 1, column=3, value=total_qty).font = Font(bold=True, color="1F4E79")
    ws2.cell(row=row_idx + 1, column=3).border = thin_border

    total_val_cell = ws2.cell(row=row_idx + 1, column=5, value=total_value)
    total_val_cell.font = Font(bold=True, color="1F4E79")
    total_val_cell.border = thin_border
    total_val_cell.number_format = "$#,##0.00"

    for col in range(1, len(pos_headers) + 1):
        max_length = len(pos_headers[col-1])
        for row in range(2, row_idx):
            cell_value = ws2.cell(row=row, column=col).value
            if cell_value:
                max_length = max(max_length, len(str(cell_value)))
        ws2.column_dimensions[get_column_letter(col)].width = min(max_length + 3, 25)

    ws2.freeze_panes = "A2"

    # ===== SHEET 3: Cost Basis Lots =====
    ws3 = wb.create_sheet("Cost Basis Lots")

    lot_headers = ["Lot ID", "Order ID", "Symbol", "Underlying", "Quantity", "Remaining",
                   "Avg Cost", "Entry Time", "Created At"]

    for col, header in enumerate(lot_headers, 1):
        cell = ws3.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    for row_idx, lot in enumerate(cost_basis_lots, 2):
        for col_idx, value in enumerate(lot, 1):
            cell = ws3.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center")

            # Avg Cost column
            if col_idx == 7:
                cell.number_format = "$#,##0.00"

            # Remaining qty - highlight if > 0
            if col_idx == 6 and value and value > 0:
                cell.font = Font(bold=True, color="1F4E79")
                cell.fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")

    for col in range(1, len(lot_headers) + 1):
        ws3.column_dimensions[get_column_letter(col)].width = 15

    ws3.freeze_panes = "A2"

    # ===== SHEET 4: Lot Matches (FIFO Sales) =====
    ws4 = wb.create_sheet("FIFO Matches")

    match_headers = ["Match ID", "Sell Order", "Lot ID", "Quantity", "Cost Basis",
                     "Sell Price", "Gain %", "Gain $", "Matched At", "Symbol", "Underlying"]

    for col, header in enumerate(match_headers, 1):
        cell = ws4.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    total_gain = 0
    for row_idx, match in enumerate(lot_matches, 2):
        for col_idx, value in enumerate(match, 1):
            cell = ws4.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center")

            # Cost Basis and Sell Price columns
            if col_idx in (5, 6):
                cell.number_format = "$#,##0.00"

            # Gain % column
            if col_idx == 7:
                cell.number_format = "0.00%"
                cell.value = value / 100 if value else 0
                if value and value > 0:
                    cell.font = profit_font
                elif value and value < 0:
                    cell.font = loss_font

            # Gain $ column
            if col_idx == 8:
                cell.number_format = "$#,##0.00"
                if value and value > 0:
                    cell.font = profit_font
                elif value and value < 0:
                    cell.font = loss_font

        if match[7]:  # gain_amount
            total_gain += match[7]

    # Total row for matches
    if lot_matches:
        total_row = len(lot_matches) + 2
        ws4.cell(row=total_row, column=7, value="TOTAL GAIN:").font = Font(bold=True)
        ws4.cell(row=total_row, column=7).alignment = Alignment(horizontal="right")
        gain_cell = ws4.cell(row=total_row, column=8, value=total_gain)
        gain_cell.number_format = "$#,##0.00"
        gain_cell.font = Font(bold=True, color="006400" if total_gain >= 0 else "8B0000")
        gain_cell.border = thin_border

    for col in range(1, len(match_headers) + 1):
        ws4.column_dimensions[get_column_letter(col)].width = 15

    ws4.freeze_panes = "A2"

    # Save file (persistent name, overwrites each time)
    filename = "trades.xlsx"
    filepath = os.path.join(OUTPUT_DIR, filename)
    wb.save(filepath)

    print(f"Exported {len(rows)} trades to: {filepath}")
    print(f"Total P/L: ${total_pl:,.2f}")
    print(f"Open positions: {len(schwab_positions)} ({total_qty:.0f} contracts)")
    print(f"Total market value: ${total_value:,.2f}")
    print(f"Cost basis lots: {len(cost_basis_lots)}")
    print(f"FIFO matches: {len(lot_matches)}")
    if lot_matches:
        print(f"Total realized gain: ${total_gain:,.2f}")
    return filepath

if __name__ == "__main__":
    export_trades()
