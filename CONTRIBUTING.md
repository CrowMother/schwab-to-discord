# Contributing to Schwab-to-Discord

This guide helps developers add new features or modify existing functionality.

## Development Setup

### Prerequisites
- Python 3.12+
- Git
- Docker Desktop (for testing)

### Local Setup

```bash
# Clone the repository
git clone https://github.com/your-repo/schwab-to-discord.git
cd schwab-to-discord

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Mac/Linux)
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"
```

### Configuration for Development

```bash
# Copy example configs
cp .env.example .env
cp .env.secrets.example config/.env.secrets

# Edit config/.env.secrets with your test credentials
```

## Architecture Overview

```
src/app/
├── core/              # Foundation layer
│   ├── config.py      # Settings dataclass (single source of truth)
│   ├── runtime.py     # Singleton settings loader
│   ├── errors.py      # Custom exceptions
│   └── logging.py     # Logging setup
│
├── api/               # External API clients
│   ├── schwab.py      # Schwab API wrapper with retry logic
│   └── positions.py   # Position fetching helpers
│
├── db/                # Database layer
│   ├── connection.py  # SQLite connection
│   ├── trades_db.py   # Trades table
│   ├── cost_basis_db.py  # FIFO lot tracking
│   └── queries.py     # Common queries
│
├── discord/           # Discord integration
│   ├── discord_webhook.py  # HTTP posting
│   └── discord_message.py  # Embed building
│
├── services/          # Service layer (lazy loading)
│   ├── registry.py    # Service registry
│   ├── schwab_service.py
│   └── discord_service.py
│
├── domain/            # Business logic
│   ├── trade_processor.py
│   ├── trade_poster.py
│   └── cost_basis.py
│
├── exports/           # Export functionality
│   └── excel_exporter.py
│
├── gsheet/            # Google Sheets integration
│   └── gsheet_client.py
│
├── scheduler/         # Scheduled tasks
│   └── gsheet_scheduler.py
│
├── models/            # Data structures
│   ├── data.py        # Trade dataclass
│   └── config.py      # Re-exports from core (backward compat)
│
├── utils/             # Helpers
│   ├── time.py
│   └── logging.py
│
├── bot.py             # Main bot orchestrator (SchwabBot class)
├── main.py            # Entry point (redirects to bot.py)
└── constants.py       # Centralized constants
```

## Adding a New Feature

### Example: Adding a New Export Format

1. **Create the exporter module:**

```python
# src/app/exports/csv_exporter.py
"""CSV export functionality."""

import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def export_trades_csv(output_path: str = "/data/trades.csv") -> None:
    """Export trades to CSV format."""
    from app.core import get_settings
    from app.db.connection import get_connection

    settings = get_settings()
    conn = get_connection(settings.db_path)

    try:
        cursor = conn.execute("SELECT * FROM trades ORDER BY entered_time DESC")
        rows = cursor.fetchall()

        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([desc[0] for desc in cursor.description])
            writer.writerows(rows)

        logger.info(f"Exported {len(rows)} trades to {output_path}")
    finally:
        conn.close()
```

2. **Add to exports __init__.py:**

```python
# src/app/exports/__init__.py
from app.exports.excel_exporter import export_trades
from app.exports.csv_exporter import export_trades_csv

__all__ = ["export_trades", "export_trades_csv"]
```

3. **Optionally add to bot.py if it should run automatically.**

### Example: Adding a New Discord Embed Style

1. **Edit discord_message.py:**

```python
# Add new color to COLOR_MAP
COLOR_MAP = {
    # ... existing colors ...
    ("CUSTOM", None): DiscordColors.SUCCESS,
}

# Add new embed builder
def build_custom_embed(data: dict) -> DiscordEmbed:
    """Build a custom embed for special notifications."""
    embed = DiscordEmbed(
        title=data.get("title", "Notification"),
        color=DiscordColors.SUCCESS
    )
    embed.add_field("Field", data.get("value", "N/A"), inline=True)
    embed.set_timestamp()
    return embed
```

### Example: Adding a New Configuration Option

1. **Add to core/config.py Settings class:**

```python
@dataclass(frozen=True)
class Settings:
    # ... existing fields ...

    # New option
    my_new_option: str
```

2. **Add to from_environ():**

```python
@classmethod
def from_environ(cls) -> "Settings":
    return cls(
        # ... existing ...
        my_new_option=_get_str("MY_NEW_OPTION", "default_value"),
    )
```

3. **Add to .env.example:**

```env
# My new feature
MY_NEW_OPTION=default_value
```

## Code Style Guidelines

### Imports
- Use `from __future__ import annotations` for type hints
- Group imports: stdlib, third-party, local
- Use TYPE_CHECKING for type-only imports

### Configuration
- All config goes through `core/config.py`
- Use `from app.core import get_settings` to access config
- Never hardcode values that could be configurable

### Error Handling
- Use custom exceptions from `core/errors.py`
- Log errors with context
- Use exponential backoff for retries

### Logging
```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Detailed info for debugging")
logger.info("Normal operation messages")
logger.warning("Something unexpected but not fatal")
logger.error("Error that needs attention")
logger.critical("Fatal error, bot will stop")
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test
pytest tests/test_config.py -v
```

## Building Docker Image

```bash
# Build locally
docker build -t schwab-to-discord:dev .

# Test locally
docker-compose up

# Push to Docker Hub
docker tag schwab-to-discord:dev crowmommy/schwab-to-discord:latest
docker push crowmommy/schwab-to-discord:latest
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `pytest`
5. Commit with descriptive message
6. Push and create PR

## Common Tasks

### Adding a new database table

1. Create migration in `db/` folder
2. Add init function to `db/__init__.py`
3. Call init in `bot.py._init_database()`

### Adding a new scheduled task

1. Create scheduler in `scheduler/` folder
2. Add start/stop functions
3. Call from `bot.py._init_scheduler()`

### Adding a new API endpoint

1. Create client in `api/` folder
2. Add service wrapper in `services/`
3. Register in `services/registry.py`

## Questions?

Open an issue on GitHub or check existing documentation in the `docs/` folder.
