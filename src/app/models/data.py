from dataclasses import dataclass


@dataclass(frozen=True)
class Trade:
    order_id: int | None
    symbol: str  # Full symbol (includes option details for options)
    underlying: str  # Just the ticker (e.g., "AAPL") for display
    instruction: str | None
    description: str | None
    asset_type: str | None
    price: float  # Actual fill price (not limit price)
    quantity: int
    filled_quantity: int
    remaining_quantity: int
    status: str | None
    entered_time: str | None
    close_time: str | None


def _extract_fill_price(data: dict) -> float:
    """
    Extract the actual fill price from Schwab order data.

    Schwab returns two price values:
    - order.price: The limit price (what you requested)
    - order.orderActivityCollection[].executionLegs[].price: The actual fill price

    For filled orders, we want the actual execution price, not the limit price.
    """
    # Try to get actual fill price from execution legs
    activities = data.get("orderActivityCollection") or []
    total_value = 0.0
    total_qty = 0.0

    for activity in activities:
        exec_legs = activity.get("executionLegs") or []
        for leg in exec_legs:
            leg_price = leg.get("price")
            leg_qty = leg.get("quantity")
            if leg_price is not None and leg_qty:
                total_value += float(leg_price) * float(leg_qty)
                total_qty += float(leg_qty)

    # Calculate weighted average fill price if we have execution data
    if total_qty > 0:
        return total_value / total_qty

    # Fall back to limit price if no execution data (pending orders, etc.)
    return float(data.get("price") or 0.0)


def load_trade(data: dict) -> Trade:
    leg = (data.get("orderLegCollection") or [{}])[0]
    inst = leg.get("instrument") or {}

    # Use full symbol for tracking (includes strike/exp for options)
    symbol = (
        inst.get("symbol")
        or data.get("symbol")
        or ""
    )

    # Use underlying for display (just the ticker)
    underlying = (
        inst.get("underlyingSymbol")
        or inst.get("symbol")
        or data.get("symbol")
        or ""
    )

    return Trade(
        order_id=_safe_int(data.get("orderId")),
        symbol=str(symbol),
        underlying=str(underlying),
        instruction=leg.get("instruction"),
        description=inst.get("description"),
        asset_type=inst.get("assetType") or leg.get("orderLegType"),
        price=_extract_fill_price(data),
        quantity=_safe_int(data.get("quantity")) or 0,
        filled_quantity=_safe_int(data.get("filledQuantity")) or 0,
        remaining_quantity=_safe_int(data.get("remainingQuantity")) or 0,
        status=data.get("status"),
        entered_time=data.get("enteredTime"),
        close_time=data.get("closeTime"),
    )

def _safe_int(x) -> int | None:
    try:
        if x is None:
            return None
        return int(float(x))  # Schwab often uses 1.0
    except (TypeError, ValueError):
        return None
