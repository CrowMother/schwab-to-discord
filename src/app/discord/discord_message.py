from __future__ import annotations

from typing import Optional


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

def build_discord_message_template(template: str, trade, state: Optional[object] = None, position_left: int = 0, total_sold: int = 0) -> str:
    """
    Compile a Discord message from a template string and a Trade dataclass.
    The template can use placeholders like {symbol}, {instruction}, etc.
    """
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
        description=getattr(trade, "description", "N/A"),
        entered_time=getattr(trade, "entered_time", "N/A"),
        close_time=getattr(trade, "close_time", "N/A"),
    )
    return message
