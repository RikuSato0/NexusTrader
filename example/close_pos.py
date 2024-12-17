import ccxt
from tradebot.constants import CONFIG



BYBIT_API_KEY = CONFIG["bybit"]["API_KEY"]
BYBIT_API_SECRET = CONFIG["bybit"]["SECRET"]

exchange = ccxt.bybit({
    "apiKey": BYBIT_API_KEY,
    "secret": BYBIT_API_SECRET,
})

pos = exchange.fetch_positions(params={"limit": 100})
print(len(pos))
for p in pos:
    symbol = p["symbol"]
    side = p["side"]
    amount = p["contracts"] * p["contractSize"]
    
    if side == "long":
        # close long position
        res = exchange.create_order(symbol, "market", "sell", amount, params={"reduceOnly": True})
    elif side == "short":
        # close short position
        res = exchange.create_order(symbol, "market","buy", amount, params={"reduceOnly": True})
    print(res)
