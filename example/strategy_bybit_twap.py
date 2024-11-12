import asyncio
from tradebot.constants import CONFIG
from tradebot.types import Order
from tradebot.constants import OrderSide, OrderType, OrderStatus
from tradebot.strategy import Strategy
from decimal import Decimal
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
        super().__init__(tick_size=1)

        self.amount = Decimal(1)
        self.symbol = "ETH/USDT:USDT"
        self.pos = Decimal(0)
        self.order_id = None
        self.finished = False

    async def on_tick(self, tick):
        if self.finished:
            return
        if self.order_id:
            order: Order = self.cache(BybitAccountType.ALL_TESTNET).get_order(
                self.order_id
            )
            print(order)
            if order.status == OrderStatus.FILLED:
                if self.pos < self.amount:
                    self.pos += order.filled
                    print(f"Filled {self.pos} of {self.amount}")
                else:
                    print("TWAP completed")
                    self.finished = True
            else:
                order_cancel = await self.cancel_order(
                    account_type=BybitAccountType.ALL_TESTNET,
                    symbol=self.symbol,
                    order_id=self.order_id,
                )
                print(order_cancel)
                if not order_cancel.success:
                    print(f"Failed to cancel order {self.order_id}")
                    order: Order = self.cache(BybitAccountType.ALL_TESTNET).get_order(
                        self.order_id
                    )
                    self.pos += order.filled

        book = self.get_bookl1("bybit", self.symbol)

        size = max(
            self.market(BybitAccountType.ALL_TESTNET)[self.symbol].limits.amount.min,
            min(book.ask_size, self.amount - self.pos),
        )
        amount = self.amount_to_precision(
            account_type=BybitAccountType.ALL_TESTNET,
            symbol=self.symbol,
            amount=size,
        )

        price = self.price_to_precision(
            account_type=BybitAccountType.ALL_TESTNET,
            symbol=self.symbol,
            price=book.ask,
        )

        if self.pos < self.amount:
            order = await self.create_order(
                account_type=BybitAccountType.ALL_TESTNET,
                symbol=self.symbol,
                side=OrderSide.BUY,
                type=OrderType.LIMIT,
                amount=amount,
                price=price,
            )
            self.order_id = order.id
            print(f"Created order {order}")


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
            strategy_id="strategy_vwap",
            user_id="test_user",
        )

        demo = Demo()
        demo.add_public_connector(conn_linear)
        demo.add_private_connector(private_conn)
        await demo.subscribe_bookl1(BybitAccountType.LINEAR_TESTNET, "ETH/USDT:USDT")
        await demo.run()

    except asyncio.CancelledError:
        print("Cancelled")
    finally:
        await conn_linear.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
