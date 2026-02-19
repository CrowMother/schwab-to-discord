# Schwab-to-Discord

A Python bot that monitors your Schwab brokerage account for filled trades and instantly posts notifications to Discord.

## Features

- Polls Schwab every 5 seconds for new filled orders
- Calculates cost basis and gain % using FIFO method
- Posts formatted notifications to Discord with color-coded embeds
- Tracks position sizes and remaining contracts
- Exports trade history to Excel and Google Sheets (optional)
- Runs in Docker for easy deployment

## Quick Start

### Prerequisites
- Docker Desktop
- Schwab Developer Account ([developer.schwab.com](https://developer.schwab.com))
- Discord server with webhook

### 1. Clone and Configure

```bash
git clone https://github.com/your-repo/schwab-to-discord.git
cd schwab-to-discord

# Copy example configs
cp .env.example .env
cp .env.secrets.example config/.env.secrets
```

### 2. Edit Configuration

Edit `config/.env.secrets` with your API keys:
```env
SCHWAB_APP_KEY=your_app_key
SCHWAB_APP_SECRET=your_app_secret
DISCORD_WEBHOOK=https://discord.com/api/webhooks/...
```

### 3. Run with Docker

```bash
docker-compose up -d
```

### First-Time Authentication

On first run, you'll need to authenticate with Schwab:
1. Check logs: `docker-compose logs -f`
2. Open the authorization URL in your browser
3. Log in to Schwab and authorize the app
4. The bot will start monitoring trades

## Documentation

| Guide | Description |
|-------|-------------|
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | Full setup guide for Windows |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Developer guide for adding features |
| [docs/](docs/) | API and module documentation |

## Project Structure

```
schwab-to-discord/
├── src/app/
│   ├── api/           # Schwab API client
│   ├── core/          # Configuration, logging, errors
│   ├── db/            # SQLite database operations
│   ├── discord/       # Discord webhook posting
│   ├── domain/        # Business logic
│   ├── exports/       # Excel/Google Sheets export
│   ├── gsheet/        # Google Sheets integration
│   ├── scheduler/     # APScheduler for periodic tasks
│   ├── services/      # Service layer
│   ├── models/        # Data models
│   ├── utils/         # Helpers
│   ├── bot.py         # Main bot orchestrator
│   └── constants.py   # Centralized constants
├── config/            # Configuration files
├── data/              # SQLite databases (gitignored)
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## Configuration Options

See [.env.example](.env.example) for all configuration options.

### Key Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `SCHWAB_APP_KEY` | Schwab API app key | Required |
| `SCHWAB_APP_SECRET` | Schwab API secret | Required |
| `DISCORD_WEBHOOK` | Discord webhook URL | Required |
| `DISCORD_WEBHOOK_2` | Secondary webhook (optional) | - |
| `TIME_DELTA_DAYS` | Days to look back for orders | 7 |
| `POLL_INTERVAL_SECONDS` | Polling frequency | 5 |

## Docker Hub

Pre-built images available at: [crowmommy/schwab-to-discord](https://hub.docker.com/r/crowmommy/schwab-to-discord)

```bash
docker pull crowmommy/schwab-to-discord:latest
```

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

```bash
# Local development
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"

# Run tests
pytest

# Run locally
python main.py
```

## License

MIT License - see LICENSE file for details.
