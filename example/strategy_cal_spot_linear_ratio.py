import asyncio
from tradebot.types import Trade
from tradebot.strategy import Strategy
from tradebot.exchange.binance import (
    BinanceAccountType,
    BinanceExchangeManager,
    BinancePublicConnector
)


class Demo(Strategy):
    def __init__(self):
        super().__init__(tick_size=0.01)

    async def on_tick(self, tick):
        spot = self.get_trade("binance","DOGE/USDT")
        linear = self.get_trade("binance","DOGE/USDT:USDT")
        if spot and linear:
            ratio = linear.price / spot.price - 1
            print(f"ratio: {ratio}")


async def main():
    try:
        exchange = BinanceExchangeManager()

        conn_spot = BinancePublicConnector(
            BinanceAccountType.SPOT,
            exchange
        )

        conn_usdm = BinancePublicConnector(
            BinanceAccountType.USD_M_FUTURE,
            exchange
        )

        demo = Demo()
        demo.add_public_connector(conn_spot)
        demo.add_public_connector(conn_usdm)

        await demo.subscribe_trade(BinanceAccountType.SPOT, "DOGE/USDT")
        await demo.subscribe_trade(BinanceAccountType.USD_M_FUTURE, "DOGE/USDT:USDT")

        await demo.run()

    except asyncio.CancelledError:
        print("Cancelled")
    finally:
        await conn_spot.disconnect()
        await conn_usdm.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
