# src/app/discord/discord_message.py
"""Discord message building for trade notifications."""

from __future__ import annotations

from typing import Optional, Tuple

from app.cost_basis import parse_strike_display, parse_expiration
from app.discord.discord_webhook import DiscordEmbed
from app.constants import DiscordColors


# Color mapping for different trade actions
COLOR_MAP = {
    ("BUY", "OPEN"): DiscordColors.TEAL,
    ("BUY", "CLOSE", "WIN"): DiscordColors.BLUE,
    ("BUY", "CLOSE", "LOSS"): DiscordColors.PURPLE,
    ("BUY", "CLOSE", None): DiscordColors.CYAN,
    ("SELL", "CLOSE", "WIN"): DiscordColors.BLUE,
    ("SELL", "CLOSE", "LOSS"): DiscordColors.PURPLE,
    ("SELL", "CLOSE", None): DiscordColors.STEEL,
    ("SELL", "OPEN"): DiscordColors.INDIGO,
    ("SELL", None, "WIN"): DiscordColors.BLUE,
    ("SELL", None, "LOSS"): DiscordColors.PURPLE,
    ("SELL", None, None): DiscordColors.STEEL,
}


def _get_color(is_buy: bool, is_open: bool, is_close: bool,
               gain_pct: Optional[float]) -> int:
    """Determine embed color based on trade type and outcome."""
    action = "BUY" if is_buy else "SELL"

    # Determine position type
    if is_open:
        position = "OPEN"
    elif is_close:
        position = "CLOSE"
    else:
        position = None

    # Determine outcome
    if gain_pct is not None:
        outcome = "WIN" if gain_pct >= 0 else "LOSS"
    else:
        outcome = None

    # Look up color, with fallbacks
    key = (action, position, outcome) if position != "OPEN" else (action, position)
    if key in COLOR_MAP:
        return COLOR_MAP[key]

    # Fallback for edge cases
    key_no_outcome = (action, position, None)
    if key_no_outcome in COLOR_MAP:
        return COLOR_MAP[key_no_outcome]

    return DiscordColors.SLATE


def _get_title(trade, is_buy: bool, is_open: bool, is_close: bool) -> str:
    """Generate embed title based on trade type."""
    action = "BUY" if is_buy else "SELL"
    underlying = trade.underlying or trade.symbol

    if is_open:
        return f"{action} TO OPEN: {underlying}"
    elif is_close:
        return f"{action} TO CLOSE: {underlying}"
    else:
        return f"{action}: {underlying}"


def build_option_embed(trade, position_left: int = 0, total_sold: int = 0,
                       gain_pct: Optional[float] = None,
                       entry_price: Optional[float] = None,
                       role_id: Optional[str] = None) -> Tuple[DiscordEmbed, str]:
    """
    Build Option Bot embed with different formats for BUY vs SELL orders.

    BUY orders show: quantity bought, filled, owned
    SELL orders show: quantity sold, filled, left to sell, gain %

    Args:
        trade: Trade dataclass instance
        position_left: Remaining position quantity
        total_sold: Total quantity sold for this symbol
        gain_pct: Percentage gain/loss for closing orders
        entry_price: Original entry price for closing orders
        role_id: Discord role ID to mention (from config)

    Returns:
        Tuple of (embed, role_mention_content)
    """
    description = trade.description or ""
    strike = parse_strike_display(description)
    expiration = parse_expiration(description)
    price = getattr(trade, "price", None)
    price_str = f"${price:.2f}" if price else "N/A"
    filled = int(trade.filled_quantity) if trade.filled_quantity else 0

    instruction = trade.instruction or ""
    is_buy = "BUY" in instruction.upper()
    is_open = "OPEN" in instruction.upper()
    is_close = "CLOSE" in instruction.upper()

    # Get color and title using helper functions
    color = _get_color(is_buy, is_open, is_close, gain_pct)
    title = _get_title(trade, is_buy, is_open, is_close)

    # Build embed
    embed = DiscordEmbed(title=title, color=color)

    # Add fields in a structured layout
    embed.add_field("Strike", strike, inline=True)
    embed.add_field("Expiration", expiration, inline=True)

    if is_buy and not is_close:
        # BUY TO OPEN format
        embed.add_field("Entry", price_str, inline=True)
        embed.add_field("Ordered", str(int(trade.quantity)), inline=True)
        embed.add_field("Filled", str(filled), inline=True)
        embed.add_field("Owned", str(position_left), inline=True)
    else:
        # SELL TO CLOSE format (or BUY TO CLOSE)
        embed.add_field("Exit", price_str, inline=True)
        embed.add_field("Sold", str(int(trade.quantity)), inline=True)
        embed.add_field("Filled", str(filled), inline=True)
        embed.add_field("Remaining", str(position_left), inline=True)

        # Show gain for closing orders
        if gain_pct is not None:
            if gain_pct >= 0:
                gain_str = f"+{gain_pct:.2f}%"
            else:
                gain_str = f"{gain_pct:.2f}%"
            embed.add_field("Gain", gain_str, inline=True)

    # Add timestamp and footer
    embed.set_timestamp()
    embed.set_footer("Option Bot")

    # Role mention goes in content (outside embed)
    role_mention = f"<@&{role_id}>" if role_id else ""

    return embed, role_mention
