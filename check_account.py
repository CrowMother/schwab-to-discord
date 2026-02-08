import os
from dotenv import load_dotenv
load_dotenv()

import schwabdev

client = schwabdev.Client(
    app_key=os.getenv("SCHWAB_APP_KEY"),
    app_secret=os.getenv("SCHWAB_APP_SECRET"),
    callback_url=os.getenv("CALLBACK_URL"),
    tokens_db=os.getenv("TOKENS_DB", "/data/tokens.db"),
    timeout=int(os.getenv("SCHWAB_TIMEOUT", 10))
)

# Get all account details with positions
resp = client.account_details_all(fields="positions")
resp.raise_for_status()
accounts = resp.json()

print("=" * 70)
print("CURRENT POSITIONS FROM SCHWAB ACCOUNT")
print("=" * 70)

for account in accounts:
    positions = account.get("securitiesAccount", {}).get("positions", [])
    
    if not positions:
        print("No open positions found.")
        continue
    
    print(f"\n{'Symbol':<20} {'Type':<10} {'Qty':<8} {'Avg Price':<12} {'Market Val':<12}")
    print("-" * 70)
    
    total_value = 0
    for pos in positions:
        instrument = pos.get("instrument", {})
        symbol = instrument.get("symbol", "N/A")
        asset_type = instrument.get("assetType", "N/A")
        qty = pos.get("longQuantity", 0) - pos.get("shortQuantity", 0)
        avg_price = pos.get("averagePrice", 0)
        market_val = pos.get("marketValue", 0)
        total_value += market_val
        
        print(f"{symbol:<20} {asset_type:<10} {qty:<8.0f} ${avg_price:<11.2f} ${market_val:<11.2f}")
    
    print("-" * 70)
    print(f"{'TOTAL':<20} {'':<10} {'':<8} {'':<12} ${total_value:<11.2f}")

print("\n" + "=" * 70)
