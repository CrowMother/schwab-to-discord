# Google Sheets Export Documentation

## Overview

The `export_to_gsheet.py` script exports SELL trades from the database to the Google Sheet "NBT Performance Tracker".

**IMPORTANT:** This script must match the EXISTING format in the Google Sheet exactly. Do NOT change the format without checking the live sheet first.

---

## Google Sheet Format (MUST MATCH EXACTLY)

| Column | Header | Format | Example |
|--------|--------|--------|---------|
| A | Posted Date | `MM/DD` (no spaces, no year) | `02/06` |
| B | Ticker | Uppercase ticker symbol | `SLV` |
| C | Exp. | `MM/DD/YYYY` | `03/20/2026` |
| D | Contract | `{strike}{c/p}` (lowercase, no space) | `90c`, `30p` |
| E | Entry | Decimal price | `2.43` |
| F | Max Exit / Stop Price | Decimal price | `3.1` |
| G | Max Exit / Stop Price Percentage | `XX.XX%` | `27.57%` |
| H | Win / Loss | `WIN`, `LOSS`, or `BREAK EVEN` | `WIN` |

### Example Row
```
['02/06', 'SLV', '03/20/2026', '90c', '2.43', '3.1', '27.57%', 'WIN']
```

---

## Rules

### 1. APPEND ONLY
- New trades are ONLY appended to the bottom of the sheet
- NEVER sort or reorder existing data
- The sheet maintains its own chronological order

### 2. Duplicate Detection
Uses a 5-part key to detect duplicates:
- `(Posted Date, Ticker, Contract, Entry, Exit)`

### 3. Win/Loss Thresholds
- `gain_pct > 5%` → WIN
- `gain_pct < -5%` → LOSS
- `-5% <= gain_pct <= 5%` → BREAK EVEN

### 4. Stats Sheet Update
After export, the script updates the "Stats" sheet with:
- Current win rate percentage
- Last updated timestamp

---

## Manual Export Commands

### Export last 7 days (weekly):
```bash
# Local
cd C:\Users\Depache\stockbot-docker\schwab-to-discord
python export_to_gsheet.py

# Docker
docker exec schwab-to-discord python export_to_gsheet.py
```

### Export ALL unsynced trades:
```bash
# Local
python export_to_gsheet.py --all

# Docker
docker exec schwab-to-discord python export_to_gsheet.py --all
```

### With custom database path:
```bash
python export_to_gsheet.py --db /path/to/trades.db
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `/data/trades.db` | Path to SQLite database |
| `GOOGLE_SHEETS_CREDENTIALS_PATH` | `/data/dulcet-abacus-481722-g8-7d60a0bb5dd7.json` | Service account JSON |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | `14DKgxt8RbQdGxLiircSCLuA0Yxh-LDDlbZYEOMMO6eA` | Sheet ID |
| `GOOGLE_SHEETS_WORKSHEET_NAME` | `Sheet1` | Tab name |

---

## Scheduled Export

The scheduler runs weekly export automatically:
- **Day:** Saturday (configurable via `GSHEET_EXPORT_DAY`)
- **Time:** 8:00 AM UTC (configurable via `GSHEET_EXPORT_HOUR`, `GSHEET_EXPORT_MINUTE`)

Configured in `.env`:
```ini
GSHEET_EXPORT_DAY=sat
GSHEET_EXPORT_HOUR=8
GSHEET_EXPORT_MINUTE=0
```

---

## Troubleshooting

### Export not running?
1. Check Docker logs: `docker logs schwab-to-discord | grep -i gsheet`
2. Verify `export_to_gsheet.py` exists in container: `docker exec schwab-to-discord ls /app/`
3. Test import: `docker exec schwab-to-discord python -c "from export_to_gsheet import export_weekly"`

### Wrong format?
Check the EXISTING sheet format first. The format documented here was correct as of Feb 2026:
- Date: `MM/DD` (no spaces)
- Contract: `30c` (lowercase c/p, no space)

### Duplicates appearing?
The dedup key uses 5 fields. If any differ slightly, it won't match:
- Date format mismatch (`02/06` vs `02 / 06`)
- Contract format mismatch (`90c` vs `90 Call`)

---

## Files

- `export_to_gsheet.py` - Main export script (root of project)
- `src/app/gsheet/gsheet_client.py` - Google Sheets API client
- `src/app/scheduler/gsheet_scheduler.py` - Scheduler that calls `export_weekly()`

---

## Data Flow

```
trades table (DB)
    ↓
lot_matches table (get entry price, P/L)
    ↓
export_to_gsheet.py (format to sheet format)
    ↓
Google Sheets API (append rows)
    ↓
Stats sheet (update win rate)
```

---

Last updated: 2026-02-15
