from __future__ import annotations

from typing import Optional

from app.cost_basis import parse_strike_display, parse_expiration


def build_discord_message(trade, state: Optional[object] = None) -> str:
    """
    Compile a Discord message from a Trade dataclass (+ optional state).
    Keep this pure: no DB, no HTTP, no side effects.
    """
    lines = [
        f"**{trade.symbol}** — {trade.instruction}",
        f"Type: `{trade.asset_type}`  Status: `{trade.status}`",
        f"Qty: `{trade.quantity}`  Filled: `{trade.filled_quantity}`  Remaining: `{trade.remaining_quantity}`",
    ]

    if getattr(trade, "price", None) is not None:
        lines.append(f"Price: `{trade.price}`")

    if getattr(trade, "description", None):
        lines.append(f"Desc: {trade.description}")

    if getattr(trade, "entered_time", None):
        lines.append(f"Entered: `{trade.entered_time}`")
    if getattr(trade, "close_time", None):
        lines.append(f"Closed: `{trade.close_time}`")

    if state is not None:
        posted = getattr(state, "posted", None)
        if posted is not None:
            lines.append(f"Posted: `{bool(posted)}`")

    return "\n".join(lines)


def build_option_bot_message(trade, position_left: int = 0, total_sold: int = 0,
                             total_bought: int = 0, gain_pct: Optional[float] = None,
                             entry_price: Optional[float] = None) -> str:
    """
    Build Option Bot message with different formats for BUY vs SELL orders.

    BUY orders show: quantity bought, filled, owned
    SELL orders show: quantity sold, filled, left to sell, gain %
    """
    description = getattr(trade, "description", "") or ""
    strike = parse_strike_display(description)
    expiration = parse_expiration(description)
    price = getattr(trade, "price", "N/A")
    filled = int(trade.filled_quantity) if trade.filled_quantity else 0

    instruction = trade.instruction or ""
    is_buy = "BUY" in instruction.upper()

    lines = [
        "**Option Bot**",
        f"Ticker: {trade.symbol}",
        f"Strike: {strike}",
        f"Expiration: {expiration}",
    ]

    if is_buy:
        # BUY order format
        lines.append(f"Entry Price: {price}")
        lines.append(f"Quantity: {int(trade.quantity)} ordered | {filled} filled | {position_left} owned")
    else:
        # SELL order format
        lines.append(f"Exit Price: {price}")
        lines.append(f"Quantity: {total_sold} sold | {filled} filled | {position_left} left to sell")

        # Only show gain for sells
        if gain_pct is not None:
            if gain_pct >= 0:
                gain_str = f"+{gain_pct:.2f}%"
            else:
                gain_str = f"{gain_pct:.2f}%"
            lines.append(f"Gain: {gain_str}")

    return "\n".join(lines)


def build_discord_message_template(template: str, trade, state: Optional[object] = None,
                                   position_left: int = 0, total_sold: int = 0,
                                   gain_pct: Optional[float] = None,
                                   entry_price: Optional[float] = None) -> str:
    """
    Compile a Discord message from a template string and a Trade dataclass.
    The template can use placeholders like {symbol}, {instruction}, etc.

    New placeholders:
    - {strike}: Strike price with C/P suffix (e.g., "9c", "550p")
    - {expiration}: Expiration date (e.g., "02/13/2026")
    - {gain_pct}: Percentage gain/loss for sells
    - {entry_price}: Original entry price for sells
    """
    description = getattr(trade, "description", "") or ""
    strike = parse_strike_display(description)
    expiration = parse_expiration(description)

    # Format gain percentage
    if gain_pct is not None:
        if gain_pct >= 0:
            gain_str = f"+{gain_pct:.2f}%"
        else:
            gain_str = f"{gain_pct:.2f}%"
    else:
        gain_str = "N/A"

    # Format entry price
    entry_price_str = f"${entry_price:.2f}" if entry_price is not None else "N/A"

    message = template.format(
        symbol=trade.symbol,
        instruction=trade.instruction,
        asset_type=trade.asset_type,
        status=trade.status,
        quantity=trade.quantity,
        filled_quantity=trade.filled_quantity,
        remaining_quantity=trade.remaining_quantity,
        position_left=position_left,
        total_sold=total_sold,
        price=getattr(trade, "price", "N/A"),
        description=description,
        strike=strike,
        expiration=expiration,
        gain_pct=gain_str,
        entry_price=entry_price_str,
        entered_time=getattr(trade, "entered_time", "N/A"),
        close_time=getattr(trade, "close_time", "N/A"),
    )
    return message
