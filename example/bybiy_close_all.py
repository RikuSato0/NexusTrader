from nexustrader.constants import CONFIG
from nexustrader.exchange.bybit import BybitExchangeManager
from pprint import pprint

BYBIT_API_KEY = CONFIG["bybit"]["API_KEY"]
BYBIT_API_SECRET = CONFIG["bybit"]["SECRET"]


config = {
    "apiKey": BYBIT_API_KEY,
    "secret": BYBIT_API_SECRET,
}

exchange = BybitExchangeManager(
    config=config,
)

positions = exchange.api.fetch_positions(params={"limit": 100})

pprint(len(positions))

for position in positions:
    side = position["side"]
    symbol = position["symbol"]
    amount = position["contractSize"] * position["contracts"]
    
    res = exchange.api.create_order(
        symbol=symbol,
        side="sell" if side == "long" else "buy",
        type="market",
        amount=amount,
    )
    
    print(res)
    
