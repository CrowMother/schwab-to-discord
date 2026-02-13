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
from datetime import datetime, timezone
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
    """Get the last N trades from database with position data."""
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


def get_position_remaining(db_path: str, symbol: str) -> int:
    """Get remaining position for a symbol from cost_basis_lots."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("""
        SELECT COALESCE(SUM(remaining_qty), 0)
        FROM cost_basis_lots
        WHERE symbol = ?
    """, (symbol,))
    result = cursor.fetchone()[0]
    conn.close()
    return int(result) if result else 0


def parse_strike(description):
    """Parse strike display from description."""
    if not description:
        return "N/A"
    parts = description.split()
    if len(parts) >= 2:
        strike_raw = parts[-2].lstrip('$')
        opt_type = parts[-1].lower()
        if opt_type == "call":
            return f"{strike_raw}c"
        elif opt_type == "put":
            return f"{strike_raw}p"
    return "N/A"


def parse_expiration(description):
    """Parse expiration date from description."""
    if not description:
        return "N/A"
    import re
    match = re.search(r'(\d{2}/\d{2}/\d{4})', description)
    return match.group(1) if match else "N/A"


def build_embed(trade, test_num: int = None, total: int = None, position_left: int = 0):
    """Build Discord embed for a trade matching Option Bot format."""
    trade_id, order_id, symbol, underlying, instruction, qty, price, entered_time, description = trade

    instruction = instruction or ""
    is_buy = "BUY" in instruction.upper()
    is_open = "OPEN" in instruction.upper()
    is_close = "CLOSE" in instruction.upper()

    # Determine color
    if is_buy and is_open:
        color = 0x008080  # Teal for BUY TO OPEN
    elif is_buy:
        color = 0x00CED1  # Cyan for other buys
    else:
        color = 0x708090  # Steel for sells

    # Build title like "BUY TO OPEN: TSLA" or "SELL TO CLOSE: APA"
    action = "BUY" if is_buy else "SELL"
    if is_open:
        title = f"{action} TO OPEN: {underlying}"
    elif is_close:
        title = f"{action} TO CLOSE: {underlying}"
    else:
        title = f"{action}: {underlying}"

    strike = parse_strike(description)
    expiration = parse_expiration(description)
    price_str = f"${price:.2f}" if price else "N/A"
    filled = int(qty) if qty else 0

    # Build fields based on trade type
    fields = [
        {"name": "Strike", "value": strike, "inline": True},
        {"name": "Expiration", "value": expiration, "inline": True},
    ]

    if is_buy and not is_close:
        # BUY TO OPEN format
        fields.extend([
            {"name": "Entry", "value": price_str, "inline": True},
            {"name": "Ordered", "value": str(filled), "inline": True},
            {"name": "Filled", "value": str(filled), "inline": True},
            {"name": "Owned", "value": str(position_left), "inline": True},
        ])
    else:
        # SELL TO CLOSE format
        fields.extend([
            {"name": "Exit", "value": price_str, "inline": True},
            {"name": "Sold", "value": str(filled), "inline": True},
            {"name": "Filled", "value": str(filled), "inline": True},
            {"name": "Remaining", "value": str(position_left), "inline": True},
        ])

    # Build footer
    footer_text = "Option Bot"
    if test_num and total:
        footer_text = f"TEST [{test_num}/{total}] • Option Bot"

    embed = {
        "title": title,
        "color": color,
        "fields": fields,
        "footer": {"text": footer_text},
        "timestamp": datetime.now(timezone.utc).isoformat()
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
        # Get actual position remaining for this symbol
        symbol = trade[2]  # symbol is index 2
        position_left = get_position_remaining(config["db_path"], symbol)
        embed = build_embed(trade, i, len(trades), position_left)

        for webhook_name, webhook_url in webhooks:
            success, status = post_to_discord(webhook_url, embed)
            status_icon = "OK" if success else "FAIL"
            print(f"  [{i}/{len(trades)}] {status_icon} {webhook_name}: HTTP {status}")
            if success:
                success_count += 1

    total_posts = len(trades) * len(webhooks)
    print(f"\nDone! {success_count}/{total_posts} posts successful.")
    print("Check Discord for test messages.")


if __name__ == "__main__":
    main()
