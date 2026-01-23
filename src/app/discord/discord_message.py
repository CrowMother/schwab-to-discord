from __future__ import annotations

from typing import Optional


def build_discord_message(trade, state: Optional[object] = None) -> str:
    """
    Compile a Discord message from a Trade dataclass (+ optional state).
    Keep this pure: no DB, no HTTP, no side effects.
    """
    # Minimal “raw but readable” foundation. You can prettify later.
    lines = [
        f"**{trade.symbol}** — {trade.instruction}",
        f"Type: `{trade.asset_type}`  Status: `{trade.status}`",
        f"Qty: `{trade.quantity}`  Filled: `{trade.filled_quantity}`  Remaining: `{trade.remaining_quantity}`",
    ]

    if getattr(trade, "price", None) is not None:
        lines.append(f"Price: `{trade.price}`")

    if getattr(trade, "description", None):
        lines.append(f"Desc: {trade.description}")

    # Timestamps
    if getattr(trade, "entered_time", None):
        lines.append(f"Entered: `{trade.entered_time}`")
    if getattr(trade, "close_time", None):
        lines.append(f"Closed: `{trade.close_time}`")

    # Optional state additions (safe placeholders for now)
    if state is not None:
        posted = getattr(state, "posted", None)
        if posted is not None:
            lines.append(f"Posted: `{bool(posted)}`")

    return "\n".join(lines)
