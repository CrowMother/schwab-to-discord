#!/usr/bin/env python3
"""Schwab to Discord Bot - Entry Point"""

import sys


def main() -> int:
    """Run the Schwab to Discord bot."""
    from app.bot import run_bot
    return run_bot()


if __name__ == "__main__":
    sys.exit(main())
