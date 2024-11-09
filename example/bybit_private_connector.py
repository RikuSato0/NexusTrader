import asyncio
from tradebot.constants import CONFIG
from tradebot.exchange.bybit import BybitPrivateConnector, BybitExchangeManager

BYBIT_API_KEY = CONFIG['bybit_testnet']['API_KEY']
BYBIT_API_SECRET = CONFIG['bybit_testnet']['SECRET']

async def main():
    try:
        config = {
            "exchange_id": "bybit",
            "apiKey": BYBIT_API_KEY,
            "secret": BYBIT_API_SECRET,
        }
        exchange = BybitExchangeManager(config)
        await exchange.load_markets()
        connector = BybitPrivateConnector(exchange, testnet=True)
        await connector.connect()
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await connector.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
