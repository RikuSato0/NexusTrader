import asyncio
from tradebot.constants import KEYS
from tradebot.exchange.bybit import BybitPrivateConnector, BybitExchangeManager, BybitAccountType

BYBIT_API_KEY = KEYS['bybit_testnet']['API_KEY']
BYBIT_API_SECRET = KEYS['bybit_testnet']['SECRET']

async def main():
    try:
        config = {
            "exchange_id": "bybit",
            "apiKey": BYBIT_API_KEY,
            "secret": BYBIT_API_SECRET,
            "sandbox": True,
        }
        exchange = BybitExchangeManager(config)
        connector = BybitPrivateConnector(exchange, BybitAccountType.ALL_TESTNET, strategy_id="test", user_id="test")
        await connector.connect()
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await connector.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
