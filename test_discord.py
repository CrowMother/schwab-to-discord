#!/usr/bin/env python3
"""
Discord Test Utility

Post test trades to Discord without role mentions for debugging.

Usage:
    python test_discord.py [--count N] [--channel primary|secondary|both]

Examples:
    python test_discord.py                  # Post last 3 trades to primary
    python test_discord.py --count 10       # Post last 10 trades
    python test_discord.py --channel both   # Post to both webhooks
"""

import argparse
import sqlite3
import requests
import os
import sys
from datetime import datetime
from dotenv import load_dotenv


def load_config():
    """Load configuration from env files."""
    # Try config directory first (new structure)
    if os.path.exists("config/.env.secrets"):
        load_dotenv("config/.env.secrets")
        load_dotenv("config/schwab-to-discord.env")
    # Fallback to root .env (old structure)
    elif os.path.exists(".env"):
        load_dotenv(".env")

    # Get DB path - handle Docker vs local paths
    db_path = os.environ.get("DB_PATH", "data/trades.db")
    # Always prefer local data/ directory when running outside Docker
    if db_path.startswith("/data/"):
        local_path = "data/" + db_path.split("/data/")[-1]
        if os.path.exists(local_path):
            db_path = local_path

    return {
        "db_path": db_path,
        "webhook_primary": os.environ.get("DISCORD_WEBHOOK"),
        "webhook_secondary": os.environ.get("DISCORD_WEBHOOK_2"),
    }


def get_trades(db_path: str, count: int = 3):
    """Get the last N trades from database."""
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("""
        SELECT trade_id, order_id, symbol, underlying, instruction,
               filled_quantity, price, entered_time, description
        FROM trades
        ORDER BY entered_time DESC
        LIMIT ?
    """, (count,))
    trades = cursor.fetchall()
    conn.close()
    return trades


def build_embed(trade, test_num: int = None, total: int = None):
    """Build Discord embed for a trade."""
    trade_id, order_id, symbol, underlying, instruction, qty, price, entered_time, description = trade

    # Determine color and action
    if instruction and "BUY" in instruction.upper():
        color = 0x00FF00  # Green
        action = "BUY"
    else:
        color = 0xFF0000  # Red
        action = "SELL"

    # Parse strike from description
    strike = "N/A"
    if description:
        parts = description.split()
        if len(parts) >= 2:
            strike_raw = parts[-2].lstrip('$')
            opt_type = parts[-1].lower()
            if opt_type == "call":
                strike = f"{strike_raw}c"
            elif opt_type == "put":
                strike = f"{strike_raw}p"

    # Build footer
    footer_text = f"TEST - Order #{order_id}"
    if test_num and total:
        footer_text = f"TEST [{test_num}/{total}] - Order #{order_id}"

    embed = {
        "title": f"{action} {underlying}",
        "description": f"**{strike}** @ **${price:.2f}**",
        "color": color,
        "fields": [
            {"name": "Qty", "value": str(int(qty)), "inline": True},
            {"name": "Symbol", "value": symbol[:30] if symbol else "N/A", "inline": True},
            {"name": "Time", "value": entered_time[:19] if entered_time else "N/A", "inline": True},
        ],
        "footer": {"text": footer_text},
        "timestamp": datetime.utcnow().isoformat()
    }
    return embed


def post_to_discord(webhook_url: str, embed: dict) -> tuple:
    """Post embed to Discord. Returns (success, status_code)."""
    if not webhook_url:
        return False, 0

    payload = {
        "content": "**[TEST]** Trade notification (no alert):",
        "embeds": [embed]
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        return resp.status_code in (200, 204), resp.status_code
    except Exception as e:
        print(f"Error posting to Discord: {e}")
        return False, 0


def main():
    parser = argparse.ArgumentParser(
        description="Post test trades to Discord without role mentions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_discord.py                  Post last 3 trades to primary webhook
  python test_discord.py --count 10       Post last 10 trades
  python test_discord.py --channel both   Post to both webhooks
  python test_discord.py -n 5 -c secondary   Post 5 trades to secondary only
        """
    )
    parser.add_argument(
        "-n", "--count",
        type=int,
        default=3,
        help="Number of recent trades to post (default: 3)"
    )
    parser.add_argument(
        "-c", "--channel",
        choices=["primary", "secondary", "both"],
        default="primary",
        help="Which webhook to post to (default: primary)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be posted without actually posting"
    )

    args = parser.parse_args()

    # Load config
    print("Loading configuration...")
    config = load_config()

    # Validate webhooks
    webhooks = []
    if args.channel in ("primary", "both"):
        if config["webhook_primary"]:
            webhooks.append(("primary", config["webhook_primary"]))
        else:
            print("Warning: Primary webhook not configured")

    if args.channel in ("secondary", "both"):
        if config["webhook_secondary"]:
            webhooks.append(("secondary", config["webhook_secondary"]))
        else:
            print("Warning: Secondary webhook not configured")

    if not webhooks:
        print("Error: No webhooks configured")
        sys.exit(1)

    # Fetch trades
    print(f"\nFetching last {args.count} trades...")
    trades = get_trades(config["db_path"], args.count)

    if not trades:
        print("No trades found in database")
        sys.exit(0)

    print(f"Found {len(trades)} trades:\n")
    for i, trade in enumerate(trades, 1):
        _, order_id, symbol, underlying, instruction, qty, price, entered_time, _ = trade
        action = "BUY" if instruction and "BUY" in instruction.upper() else "SELL"
        print(f"  {i}. {action} {int(qty)}x {underlying} @ ${price:.2f} ({entered_time[:10]})")

    if args.dry_run:
        print("\n[DRY RUN] Would post to:", ", ".join(w[0] for w in webhooks))
        print("Exiting without posting.")
        sys.exit(0)

    # Post to Discord
    print(f"\nPosting to Discord ({', '.join(w[0] for w in webhooks)})...\n")

    success_count = 0
    for i, trade in enumerate(trades, 1):
        embed = build_embed(trade, i, len(trades))

        for webhook_name, webhook_url in webhooks:
            success, status = post_to_discord(webhook_url, embed)
            status_icon = "✓" if success else "✗"
            print(f"  [{i}/{len(trades)}] {status_icon} {webhook_name}: HTTP {status}")
            if success:
                success_count += 1

    total_posts = len(trades) * len(webhooks)
    print(f"\nDone! {success_count}/{total_posts} posts successful.")
    print("Check Discord for test messages.")


if __name__ == "__main__":
    main()
