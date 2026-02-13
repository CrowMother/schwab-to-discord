# schwab-to-discord

A small Python app that:
1) Fetches Schwab orders
2) Normalizes them into dataclasses
3) Dedupes via SQLite
4) Posts updates to Discord (webhook)

## Requirements
- Python 3.12.3+
- Environment variables set (see below)

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```
## Docker
- Docker hub [Docker Hub](https://hub.docker.com/repository/docker/crowmommy/schwab-to-discord/general)
