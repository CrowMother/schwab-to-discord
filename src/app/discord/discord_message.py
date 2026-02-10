from __future__ import annotations

from typing import Optional

from app.cost_basis import parse_strike_display, parse_expiration


def build_option_bot_message(trade, position_left: int = 0, total_sold: int = 0,
                             gain_pct: Optional[float] = None,
                             entry_price: Optional[float] = None) -> str:
    """
    Build Option Bot message with different formats for BUY vs SELL orders.

    BUY orders show: quantity bought, filled, owned
    SELL orders show: quantity sold, filled, left to sell, gain %
    """
    description = trade.description or ""
    strike = parse_strike_display(description)
    expiration = parse_expiration(description)
    price = getattr(trade, "price", "N/A")
    filled = int(trade.filled_quantity) if trade.filled_quantity else 0

    instruction = trade.instruction or ""
    is_buy = "BUY" in instruction.upper()

    lines = [
        "**Option Bot**",
        f"Ticker: {trade.underlying}",
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

    # Add role mention at the end
    lines.append("")
    lines.append("<@&1403776397843103884>")

    return "\n".join(lines)
