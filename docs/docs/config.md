
---

## `docs/config.md`

```md
# Config

## `Config` (dataclass)
**What it does:** Stores all runtime settings in one immutable object.

**Needs to run:**
- Environment variables available at runtime.
- Helper functions `_opt_str()` and `_opt_int()` implemented in `app/models/helpers.py` (or equivalent).

### Fields
- `app_name: str` — name shown in logs
- `schwab_app_key: str` — Schwab developer app key
- `schwab_app_secret: str` — Schwab developer secret
- `discord_webhook: str` — Discord webhook URL
- `discord_channel: str | None` — optional; not needed for webhooks
- `db_path: str` — sqlite path for dedupe DB
- `callback_url: str` — used for Schwab auth callback flows
- `tokens_db: str` — path to tokens storage DB/file
- `schwab_timeout: int` — HTTP timeout seconds (default 10)
- `call_on_auth: str | None` — optional behavior hook
- `time_delta_days: int` — default lookback window (default 7)
- `status: str | None` — order status filter, e.g. FILLED/WORKING/etc.

---

## `load_config() -> Config`
**What it does:** Reads env vars and returns a `Config`. Fails fast if required vars are missing.

**Needs to run:**
- OS env vars set
- `_opt_str()` and `_opt_int()` available
- (Optional) `.env` loader if you support local dev (python-dotenv)

**Side effects:**
- None (just reads environment)
