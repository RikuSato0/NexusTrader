import asyncio
from decimal import Decimal
from nexustrader.constants import KEYS
from nexustrader.exchange.okx import (
    OkxAccountType,
    OkxPrivateConnector,
    OkxExchangeManager,
)

from nexustrader.constants import OrderSide, OrderType, PositionSide


OKX_API_KEY = KEYS["okex_demo"]["API_KEY"]
OKX_SECRET = KEYS["okex_demo"]["SECRET"]
OKX_PASSPHRASE = KEYS["okex_demo"]["PASSPHRASE"]


async def main():
    try:
        config = {
            "exchange_id": "okx",
            "sandbox": True,
            "apiKey": OKX_API_KEY,
            "secret": OKX_SECRET,
            "password": OKX_PASSPHRASE,
            "enableRateLimit": False,
        }

        exchange = OkxExchangeManager(config)
        connector = OkxPrivateConnector(
            account_type=OkxAccountType.DEMO,
            exchange=exchange,
        )

        await connector.connect()
        await asyncio.sleep(10)  # wait for the connection to be established

        print("placing order...")
        order = await connector.create_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            amount=Decimal("0.1"),
            price=Decimal("80000"),
            position_side=PositionSide.LONG,
        )

        print(order)

        await asyncio.sleep(5)
        print("canceling order...")
        order = await connector.cancel_order(
            symbol="BTC/USDT:USDT",
            order_id=order.id,
        )

        print(order)

        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        await connector.disconnect()
        print("Connection closed.")


if __name__ == "__main__":
    asyncio.run(main())
