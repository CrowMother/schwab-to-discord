# Trade Model

## `Trade` (dataclass)
**What it does:** Holds a normalized representation of a Schwab order/trade.

Suggested minimum fields (based on your log example):
- `order_id: int | None`
- `status: str | None`
- `entered_time: str | None`
- `close_time: str | None`
- `symbol: str` (usually underlying)
- `put_call: str | None`
- `strike: float | None`
- `expiration: str | None`
- `instruction: str | None` (BUY_TO_OPEN, SELL_TO_CLOSE, etc.)
- `quantity: float | None`
- `filled_quantity: float | None`
- `price: float | None`
- `asset_type: str | None` (OPTION/STOCK)

---

## `load_trade(data: dict) -> Trade`
**What it does:** Converts raw Schwab order JSON into a `Trade`.

**Needs to run:**
- A Schwab order dict shaped like:
  - `orderId`, `status`, `enteredTime`
  - `orderLegCollection[0].instrument` (for option details)
  - `orderActivityCollection` (for fills, if present)

**Behavior notes:**
- Prefer reading `orderId` directly (stable dedupe key).
- Prefer underlying symbol from:
  - `orderLegCollection[0].instrument.underlyingSymbol`
  - fallback: parse from option symbol if needed

**Side effects:**
- None (pure function)
