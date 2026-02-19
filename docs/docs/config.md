# Configuration System

The application uses a unified configuration system located in `app/core/config.py`.

---

## `Settings` (dataclass)

**Location:** `app/core/config.py`

**What it does:** Stores all runtime settings in one immutable object.

**How to access:**
```python
from app.core import get_settings

settings = get_settings()
print(settings.app_name)
print(settings.discord_webhook)
```

### Fields

#### Application
- `app_name: str` — Name shown in logs (default: "Schwab to Discord")
- `log_level: str` — Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)

#### Schwab API
- `schwab_app_key: str` — Schwab developer app key (REQUIRED)
- `schwab_app_secret: str` — Schwab developer secret (REQUIRED)
- `schwab_callback_url: str` — OAuth callback URL (default: https://127.0.0.1)
- `schwab_timeout: int` — HTTP timeout in seconds (default: 30)
- `time_delta_days: int` — Days to look back for orders (default: 7)
- `order_status: str` — Order status filter: FILLED, PENDING, etc. (default: FILLED)
- `poll_interval: int` — Seconds between polling (default: 5)
- `tokens_db: str` — Path to tokens database (default: /data/tokens.db)
- `call_on_auth: str | None` — Optional callback for auth events

#### Discord
- `discord_webhook: str` — Primary webhook URL (REQUIRED)
- `discord_webhook_2: str` — Secondary webhook URL (optional)
- `discord_role_id: str` — Role ID to mention (optional)
- `discord_channel_id: str | None` — Channel ID (optional)
- `template: str | None` — Custom message template (optional)

#### Database
- `db_path: str` — SQLite database path (default: /data/trades.db)
- `export_path: str` — Excel export path (default: /data/trades.xlsx)

#### Google Sheets (optional)
- `gsheet_credentials_path: str | None` — Path to service account JSON
- `gsheet_spreadsheet_id: str | None` — Spreadsheet ID from URL
- `gsheet_worksheet_name: str` — Worksheet name (default: Sheet1)
- `gsheet_export_day: str` — Day for export: mon-sun (default: sat)
- `gsheet_export_hour: int` — Hour for export 0-23 (default: 8)
- `gsheet_export_minute: int` — Minute for export 0-59 (default: 0)

### Properties

- `gsheet_enabled: bool` — True if Google Sheets is configured
- `callback_url: str` — Alias for schwab_callback_url
- `discord_webhook_secondary: str` — Alias for discord_webhook_2
- `status: str` — Alias for order_status

---

## `get_settings() -> Settings`

**Location:** `app/core/runtime.py`

**What it does:** Returns the singleton Settings instance. Loads configuration on first call.

**Usage:**
```python
from app.core import get_settings

settings = get_settings()
```

**Load order:**
1. `config/schwab-to-discord.env` — Base configuration (committed to git)
2. `config/.env.secrets` — Secrets (gitignored)
3. Process environment variables — Override any value

---

## Backward Compatibility

The old `Config` class and `load_config()` function are still available for backward compatibility:

```python
# Old way (still works)
from app.models.config import Config, load_config
config = load_config()

# New way (recommended)
from app.core import Settings, get_settings
settings = get_settings()
```

Both return the same data - `models/config.py` now re-exports from `core/config.py`.
