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
    
    async def on_tick(self, tick):
        linear_bid = self.get_bookl1("bybit", "BTC/USDT:USDT").bid
        spot_ask = self.get_bookl1("bybit", "BTC/USDT").ask
        linear_ask = self.get_bookl1("bybit", "BTC/USDT:USDT").ask
        spot_bid = self.get_bookl1("bybit", "BTC/USDT").bid
        
        open_ratio = linear_bid / spot_ask - 1
        close_ratio = linear_ask / spot_bid - 1
        print(f"Open Ratio: {open_ratio} Close Ratio: {close_ratio}")
        


async def main():
    try:
        exchange = BybitExchangeManager({"exchange_id": "bybit"})


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
        await conn_spot.disconnect()
        await conn_linear.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
