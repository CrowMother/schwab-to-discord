# Schwab API

## `SchwabApi`
**What it does:** Thin wrapper around the Schwab client library. No parsing, no DB, no Discord.

**Needs to run:**
- Schwab client dependency installed (your chosen library)
- Auth/tokens available (however your library handles it)
- Config contains keys/secrets and callback info if required

---

## `get_orders(config) -> list[dict]`
**What it does:** Calls Schwab “get orders” endpoint and returns raw JSON list.

**Needs to run:**
- Valid Schwab auth
- A time window (either computed in here, or passed in)

**Side effects:**
- HTTP request(s)

**Errors:**
- Should raise if HTTP fails (don’t swallow)
