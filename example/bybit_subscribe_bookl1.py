import asyncio
from tradebot.types import BookL1
from tradebot.strategy import Strategy
from tradebot.exchange.bybit import (
    BybitPublicConnector,
    BybitAccountType,
    BybitExchangeManager,
)


class Demo(Strategy):
    def __init__(self):
        super().__init__(tick_size=0.01)
        self.market = {}

    def _on_bookl1(self, bookl1: BookL1):
        self.market[bookl1.symbol] = bookl1
    
    def on_tick(self, tick):
        linear_bid = self.market["BTC/USDT:USDT"].bid
        spot_ask = self.market["BTC/USDT"].ask
        ratio = linear_bid / spot_ask - 1
        print(f"Ratio: {ratio}")
        


async def main():
    try:
        exchange = BybitExchangeManager({"exchange_id": "bybit"})
        await exchange.load_markets()  # get `market` and `market_id` data

        conn_spot = BybitPublicConnector(
            BybitAccountType.SPOT,
            exchange
        )

        conn_linear = BybitPublicConnector(
            BybitAccountType.LINEAR,
            exchange
        )

        demo = Demo()
        demo.add_public_connector(conn_spot)
        demo.add_public_connector(conn_linear)

        await demo.subscribe_bookl1(BybitAccountType.SPOT, "BTC/USDT")
        await demo.subscribe_bookl1(BybitAccountType.LINEAR, "BTC/USDT:USDT")
        await demo.run()

    except asyncio.CancelledError:
        print("Cancelled")
    finally:
        await exchange.close()
        await conn_spot.disconnect()
        await conn_linear.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
