from dataclasses import dataclass# kept for consistent file style (not used here)

@dataclass(frozen=True)
class Trade:
    order_id: int | None
    symbol: str
    instruction: str | None
    asset_type: str | None
    price: float
    quantity: int
    filled_quantity: int
    remaining_quantity: int
    status: str | None
    entered_time: str | None
    close_time: str | None

def load_trade(data: dict) -> Trade:
    leg = (data.get("orderLegCollection") or [{}])[0]
    inst = leg.get("instrument") or {}

    # Prefer underlyingSymbol for options, otherwise instrument symbol.
    symbol = (
        inst.get("underlyingSymbol")
        or inst.get("symbol")
        or data.get("symbol")
        or ""
    )

    return Trade(
        order_id=_safe_int(data.get("orderId")),
        symbol=str(symbol),
        instruction=leg.get("instruction"),
        asset_type=inst.get("assetType") or leg.get("orderLegType"),
        price=float(data.get("price") or 0.0),
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
