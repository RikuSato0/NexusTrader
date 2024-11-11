import asyncio
from tradebot.constants import CONFIG
from tradebot.types import BookL1
from tradebot.strategy import Strategy
from tradebot.exchange.bybit import (
    BybitPublicConnector,
    BybitPrivateConnector,
    BybitAccountType,
    BybitExchangeManager,
)

BYBIT_API_KEY = CONFIG['bybit_testnet_2']['API_KEY']
BYBIT_API_SECRET = CONFIG['bybit_testnet_2']['SECRET']

class Demo(Strategy):
    def __init__(self):
        super().__init__(tick_size=0.01)
        self.market = {}

    def _on_bookl1(self, bookl1: BookL1):
        # print(f"BookL1: {bookl1}")
        self.market[bookl1.symbol] = bookl1
    
    def on_tick(self, tick):
        pass
        


async def main():
    try:
        
        config = {
            "apiKey": BYBIT_API_KEY,
            "secret": BYBIT_API_SECRET,
            "sandbox": True,
        }
        
        exchange = BybitExchangeManager(config)


        conn_linear = BybitPublicConnector(
            BybitAccountType.LINEAR_TESTNET,
            exchange
        )
        
        private_conn = BybitPrivateConnector(
            exchange,
            testnet=True,
            strategy_id="strategy_vwap",
            user_id="test_user"
        )

        demo = Demo()
        demo.add_public_connector(conn_linear)
        demo.add_private_connector(private_conn)
        await demo.subscribe_bookl1(BybitAccountType.LINEAR, "BTC/USDT:USDT")
        await demo.run()

    except asyncio.CancelledError:
        print("Cancelled")
    finally:
        await conn_linear.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
