import ccxt
import os
import json

def generate_markets(exchange_id: str, output_dir: str):
    exchange = getattr(ccxt, exchange_id)()
    markets = exchange.load_markets()
    with open(os.path.join(output_dir, f"{exchange_id}_markets.json"), "w") as f:
        json.dump(markets, f, indent=4)
    
def main():
    output_dir = os.path.join("test", "test_data")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    generate_markets("bybit", output_dir)
    

if __name__ == "__main__":
    main()
