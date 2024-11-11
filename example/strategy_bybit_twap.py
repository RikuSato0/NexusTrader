import asyncio
from tradebot.constants import CONFIG
from tradebot.types import BookL1
from tradebot.constants import OrderSide, OrderType
from tradebot.strategy import Strategy
from tradebot.exchange.bybit import (
    BybitPublicConnector,
    BybitPrivateConnector,
    BybitAccountType,
    BybitExchangeManager,
)

BYBIT_API_KEY = CONFIG["bybit_testnet_2"]["API_KEY"]
BYBIT_API_SECRET = CONFIG["bybit_testnet_2"]["SECRET"]


class Demo(Strategy):
    def __init__(self):
        super().__init__(tick_size=0.5)
        n = 20
        buy_amount = 0.5
        self.amount = buy_amount / n
        self.symbol = "BTC/USDT:USDT"
        self.market = {}
        self.pos = 0

    def _on_bookl1(self, bookl1: BookL1):
        self.market[bookl1.symbol] = bookl1

    async def on_tick(self, tick):
        if self.pos < 20:
            amount = self.amount_to_precision(
                account_type=BybitAccountType.ALL_TESTNET,
                symbol=self.symbol,
                amount=self.amount,
            )
            await self.create_order(
                account_type=BybitAccountType.ALL_TESTNET,
                symbol=self.symbol,
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                amount=amount,
            )
            self.pos += 1
            


async def main():
    try:
        config = {
            "apiKey": BYBIT_API_KEY,
            "secret": BYBIT_API_SECRET,
            "sandbox": True,
        }

        exchange = BybitExchangeManager(config)

        conn_linear = BybitPublicConnector(BybitAccountType.LINEAR_TESTNET, exchange)

        private_conn = BybitPrivateConnector(
            exchange,
            account_type=BybitAccountType.ALL_TESTNET,
            strategy_id="strategy_twap",
            user_id="test_user",
        )

        demo = Demo()
        demo.add_public_connector(conn_linear)
        demo.add_private_connector(private_conn)
        await demo.subscribe_bookl1(BybitAccountType.LINEAR_TESTNET, "BTC/USDT:USDT")
        await private_conn.connect()
        await asyncio.sleep(10) # wait to connect
        
        await demo.run()

    except asyncio.CancelledError:
        print("Cancelled")
    finally:
        await conn_linear.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
