import ccxt
import json
import os

file_path = os.path.join("test", "test_data", "binance_markets.json")

binance = ccxt.binance()
markets = binance.load_markets()

if not os.path.exists(file_path):
    with open(file_path, "w") as f:
        json.dump(markets, f, indent=2)

file_path = os.path.join("test", "test_data", "okx_markets.json")

okx = ccxt.okx()
markets = okx.load_markets()

if not os.path.exists(file_path):
    with open(file_path, "w") as f:
        json.dump(markets, f, indent=2)






