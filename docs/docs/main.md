# main.py

## `main() -> None`
**What it does:**
- Calls `setup_logging()`
- Loads config via `load_config()`
- Creates Schwab API client
- Fetches raw orders
- Converts each order into a `Trade` via `load_trade()`
- (Later) dedupes + posts to Discord

**Needs to run:**
- Valid Config env vars
- Schwab client working (auth/tokens handled)
- `setup_logging()` implemented
- `SchwabApi` implemented
- `load_trade()` implemented

**Side effects:**
- Writes logs
- Makes HTTP calls to Schwab
- Eventually writes to SQLite and posts to Discord
