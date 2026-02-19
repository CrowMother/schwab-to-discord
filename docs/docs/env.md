# Environment Configuration

This app reads configuration from environment variables, organized into two files:
- `config/schwab-to-discord.env` — Non-secret settings (committed to git)
- `config/.env.secrets` — API keys and secrets (gitignored)

---

## File Structure

```
schwab-to-discord/
├── config/
│   ├── schwab-to-discord.env      # Base config (safe to commit)
│   ├── .env.secrets               # Secrets (NEVER commit)
│   └── .env.secrets.example       # Template for secrets
├── data/
│   ├── tokens.db                  # Schwab OAuth tokens (gitignored)
│   ├── trades.db                  # Trade history (gitignored)
│   └── credentials.json           # Google Cloud credentials (gitignored)
└── ...
```

---

## Quick Setup

### Step 1: Copy the secrets template
```bash
cp config/.env.secrets.example config/.env.secrets
```

### Step 2: Edit `config/.env.secrets`
Fill in your actual API keys and webhooks.

### Step 3: Done!
The base config in `schwab-to-discord.env` has sensible defaults.

---

## Configuration Files

### `config/schwab-to-discord.env` (Committed to git)

Contains non-sensitive settings that are safe to share:

```env
# Application
APP_NAME=Schwab to Discord
LOG_LEVEL=INFO

# Polling settings
TIME_DELTA_DAYS=7
SCHWAB_TIMEOUT=10
ORDER_STATUS=FILLED
POLL_INTERVAL_SECONDS=5

# Database paths (Docker paths)
DB_PATH=/data/trades.db
TOKENS_DB=/data/tokens.db
EXPORT_PATH=/data/trades.xlsx

# Google Sheets schedule
GOOGLE_SHEETS_WORKSHEET_NAME=Sheet1
GSHEET_EXPORT_DAY=sat
GSHEET_EXPORT_HOUR=8
GSHEET_EXPORT_MINUTE=0
```

### `config/.env.secrets` (NEVER commit)

Contains sensitive API keys and credentials:

```env
# Schwab API (REQUIRED)
SCHWAB_APP_KEY=your_app_key_here
SCHWAB_APP_SECRET=your_app_secret_here
CALLBACK_URL=https://127.0.0.1

# Discord (REQUIRED)
DISCORD_WEBHOOK=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_2=                    # Optional secondary webhook
DISCORD_CHANNEL_ID=                   # Optional
DISCORD_ROLE_ID=                      # Optional

# Google Sheets (OPTIONAL)
GOOGLE_SHEETS_CREDENTIALS_PATH=/data/credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
```

---

## Environment Variables Reference

### Required Variables

| Variable | Description |
|----------|-------------|
| `SCHWAB_APP_KEY` | Your Schwab Developer App Key |
| `SCHWAB_APP_SECRET` | Your Schwab Developer App Secret |
| `DISCORD_WEBHOOK` | Discord webhook URL for trade alerts |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | Schwab to Discord | Name shown in logs |
| `LOG_LEVEL` | INFO | DEBUG, INFO, WARNING, ERROR |
| `TIME_DELTA_DAYS` | 7 | Days to look back for orders |
| `SCHWAB_TIMEOUT` | 10 | API timeout in seconds |
| `ORDER_STATUS` | FILLED | Filter: FILLED, PENDING, etc. |
| `POLL_INTERVAL_SECONDS` | 5 | Seconds between checks |
| `CALLBACK_URL` | https://127.0.0.1 | OAuth callback URL |
| `DB_PATH` | /data/trades.db | Trade history database |
| `TOKENS_DB` | /data/tokens.db | Schwab OAuth tokens |
| `EXPORT_PATH` | /data/trades.xlsx | Excel export path |
| `DISCORD_WEBHOOK_2` | (empty) | Secondary webhook |
| `DISCORD_CHANNEL_ID` | (empty) | Channel for bot messages |
| `DISCORD_ROLE_ID` | (empty) | Role to mention |
| `GOOGLE_SHEETS_CREDENTIALS_PATH` | (empty) | Service account JSON path |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | (empty) | Target spreadsheet ID |
| `GOOGLE_SHEETS_WORKSHEET_NAME` | Sheet1 | Worksheet name |
| `GSHEET_EXPORT_DAY` | sat | Export day (mon-sun) |
| `GSHEET_EXPORT_HOUR` | 8 | Export hour (0-23) |
| `GSHEET_EXPORT_MINUTE` | 0 | Export minute (0-59) |

---

## Docker Deployment

The `docker-compose.yml` loads both config files:

```yaml
services:
  schwab-to-discord:
    env_file:
      - config/schwab-to-discord.env
      - config/.env.secrets
    volumes:
      - ./data:/data
```

The `/data` volume persists:
- `tokens.db` — Schwab OAuth tokens (refresh weekly)
- `trades.db` — Trade history and cost basis
- `trades.xlsx` — Excel export
- `credentials.json` — Google Cloud service account

---

## Loading Order

Environment variables are loaded in this order (later overrides earlier):

1. `config/schwab-to-discord.env` — Base defaults
2. `config/.env.secrets` — Your secrets (overrides base)
3. Process environment — Docker/CI overrides (highest priority)

This allows you to:
- Commit sensible defaults in the base config
- Keep secrets in a separate gitignored file
- Override anything via Docker environment variables
