import asyncio
from decimal import Decimal

from nexustrader.constants import KEYS
from nexustrader.constants import OrderSide, OrderType
from nexustrader.exchange.bybit import (
    BybitExchangeManager,
    BybitPrivateConnector,
    BybitAccountType,
)

BYBIT_API_KEY = KEYS["bybit_testnet_2"]["API_KEY"]
BYBIT_API_SECRET = KEYS["bybit_testnet_2"]["SECRET"]


async def main():
    try:
        config = {
            "apiKey": BYBIT_API_KEY,
            "secret": BYBIT_API_SECRET,
            "sandbox": True,
        }
        exchange = BybitExchangeManager(
            config=config,
        )
        connector = BybitPrivateConnector(
            exchange,
            BybitAccountType.UNIFIED_TESTNET,
            strategy_id="strategy_01",
            user_id="test_user",
        )
        await connector.connect()
        await asyncio.sleep(10)
        order = await connector.create_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.SELL,
            type=OrderType.MARKET,
            amount=Decimal("0.005"),
            reduce_only=True,
        )
        print(order)

        await asyncio.sleep(10)

    except asyncio.CancelledError:
        print("CancelledError")
    finally:
        await connector.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
