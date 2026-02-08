# Code Review: schwab-to-discord

**Date:** 2026-02-08
**Reviewer:** Claude Code
**Branch:** feature/position-tracking-export

---

## Summary

Overall the codebase is functional and well-structured. However, after adding the FIFO cost basis tracking and new message formats, there are some cleanup opportunities. Most are low-effort improvements that will make the code easier to maintain.

| Issue Type | Count | Priority |
|-----------|-------|----------|
| Dead/Unused Code | 4 | HIGH |
| Duplicate Logic | 4 | HIGH |
| Functions Too Long | 3 | MEDIUM |
| Inconsistent Patterns | 4 | MEDIUM |
| Missing Error Handling | 4 | MEDIUM |
| Unused Imports | 3 | LOW |
| Anti-patterns | 6 | MEDIUM |

---

## HIGH PRIORITY - Dead/Unused Code

### 1. Unused Function: `build_discord_message()`
- **File:** `src/app/discord/discord_message.py` (lines 8-35)
- **Issue:** Old generic message builder, never called anywhere
- **Action:** Delete entire function

### 2. Unused Function: `build_discord_message_template()`
- **File:** `src/app/discord/discord_message.py` (lines 83-132)
- **Issue:** Template-based approach replaced by `build_option_bot_message()`
- **Action:** Delete entire function

### 3. Unused Function: `insert_trade()`
- **File:** `src/app/db/trades_repo.py` (lines 143-148)
- **Issue:** Never called; `store_trade()` is used instead
- **Action:** Delete entire function

### 4. Unused Parameter: `total_bought`
- **File:** `src/app/discord/discord_message.py` line 39
- **Issue:** Parameter in `build_option_bot_message()` is accepted but never used
- **Action:** Remove parameter from function signature

---

## HIGH PRIORITY - Duplicate Logic

### 1. Duplicate "Extract Underlying Symbol" Logic
**The same code appears 5 times:**
```python
symbol.split()[0] if " " in symbol else symbol
```

| File | Lines |
|------|-------|
| `src/app/main.py` | 42, 55, 109 |
| `export_trades.py` | 112, 171 |
| `src/app/cost_basis.py` | 31-33 (already a function) |

**Action:** Use the existing `extract_underlying()` from `cost_basis.py` everywhere

### 2. Duplicate Schwab Position Fetching
- `src/app/main.py` lines 23-50: `get_schwab_positions()`
- `export_trades.py` lines 74-117: `get_schwab_positions()`

**Action:** Create shared module `src/app/api/positions.py`

### 3. Duplicate Gain Calculation Query
- `src/app/db/cost_basis_db.py` lines 133-141
- `export_trades.py` lines 64-72

**Action:** Have `export_trades.py` call the existing DB function

---

## MEDIUM PRIORITY - Functions Too Long

### 1. `export_trades()` - 327 lines
- **File:** `export_trades.py` (lines 119-445)
- **Issue:** Handles database queries, API calls, Excel formatting, all in one function
- **Action:** Split into smaller functions:
  - `gather_trade_data(conn)`
  - `format_trades_sheet(ws, trades)`
  - `format_positions_sheet(ws, positions)`
  - `format_cost_basis_sheet(ws, lots)`
  - `format_fifo_matches_sheet(ws, matches)`

### 2. `send_unposted_trades()` - 47 lines
- **File:** `src/app/main.py` (lines 98-144)
- **Action:** Extract data gathering and webhook posting into separate functions

---

## MEDIUM PRIORITY - Inconsistent Patterns

### 1. Datetime Imports Inside Functions
- **File:** `src/app/db/cost_basis_db.py` lines 74, 111
- **Issue:** `from datetime import datetime, timezone` imported inside functions
- **Action:** Move to module-level imports

### 2. Print Statement in Production Code
- **File:** `src/app/main.py` line 165
- **Code:** `print(f"client created: {client}")`
- **Action:** Replace with `logger.info()`

### 3. Silent Exception Handling
- **File:** `export_trades.py` lines 39-40, 45-56, 71-72
- **Code:** `except sqlite3.OperationalError: return []`
- **Action:** Log warnings before returning empty

---

## LOW PRIORITY - Unused Imports

### 1. Remove from `src/app/cost_basis.py`
```python
# Line 7: Remove Tuple
from typing import Optional  # Remove ", Tuple"
```

### 2. Update `src/app/main.py` line 12
```python
# Current:
from app.discord.discord_message import build_discord_message, build_discord_message_template, build_option_bot_message

# Should be:
from app.discord.discord_message import build_option_bot_message
```

### 3. Move `import re` to module level
- **File:** `src/app/cost_basis.py` line 188
- **Action:** Move to top of file with other imports

---

## LOW PRIORITY - Simplifications

### 1. Overly Defensive Attribute Access
```python
# Current (line 47):
description = getattr(trade, "description", "") or ""

# Simplified:
description = trade.description or ""
```

### 2. Magic Numbers
Create `src/app/constants.py`:
```python
OPTION_CONTRACT_MULTIPLIER = 100
```

Use in:
- `export_trades.py` line 159
- `src/app/cost_basis.py` lines 97-98

---

## ANTI-PATTERNS TO FIX

### 1. Catching Too Broad Exceptions
- **File:** `src/app/main.py` lines 175-177
- **Current:** `except Exception as e:`
- **Better:** `except (ConnectionError, requests.RequestException) as e:`

### 2. No Connection Cleanup on Errors
- **File:** `export_trades.py`
- **Issue:** `conn.close()` only in happy path
- **Action:** Use `try/finally` or context manager

---

## Quick Wins (Do These First)

1. **Delete dead functions** (3 functions, ~100 lines removed)
2. **Remove unused imports** (3 imports)
3. **Remove unused `total_bought` parameter**
4. **Move datetime/re imports to module level**
5. **Replace print with logger.info**

Estimated time: ~15 minutes
Lines removed: ~100+
Risk: Very low

---

## Files Changed Summary

| File | Changes Needed |
|------|----------------|
| `src/app/discord/discord_message.py` | Remove 2 functions, 1 parameter |
| `src/app/main.py` | Clean imports, replace print |
| `src/app/db/trades_repo.py` | Remove 1 function |
| `src/app/cost_basis.py` | Clean imports, move re to top |
| `export_trades.py` | Add error logging, consolidate functions (optional) |

---

## Conclusion

The codebase is in good shape. The recommended cleanups are mostly removing dead code left over from the template-based approach. The highest impact changes are:

1. Removing the 3 unused functions (~100 lines)
2. Consolidating the duplicate `extract_underlying()` logic
3. Cleaning up imports

These changes will make the code easier to maintain without changing any functionality.
