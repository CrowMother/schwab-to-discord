# src/app/main.py
"""
Application entry point - redirects to bot.py.

This module exists for backward compatibility. The main bot logic
is in app/bot.py which uses the SchwabBot class.

Usage:
    python -m app.main
    # or
    from app.main import main; main()
"""

from __future__ import annotations

import sys


def main() -> int:
    """
    Run the Schwab to Discord bot.

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    from app.bot import run_bot
    return run_bot()


if __name__ == "__main__":
    sys.exit(main())
