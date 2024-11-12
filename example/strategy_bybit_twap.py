import asyncio
from typing import Dict
from tradebot.constants import CONFIG
from tradebot.types import BookL1, Order
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
        super().__init__(tick_size=0.5)
        
        self.amount = Decimal(0.5)
        self.symbol = "BTC/USDT:USDT"
        self.market: Dict[str, BookL1] = {}
        self.pos = Decimal(0)
        self.order_id = None
        self.finished = False

    def _on_bookl1(self, bookl1: BookL1):
        self.market[bookl1.symbol] = bookl1

    async def on_tick(self, tick):
        if self.finished:
            return
        if self.order_id:
            order: Order = self._private_connectors[BybitAccountType.ALL_TESTNET].cache.get_order(self.order_id)
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
                    order: Order = self._private_connectors[BybitAccountType.ALL_TESTNET].cache.get_order(self.order_id)
                    self.pos += order.filled
                

        ask = self.market[self.symbol].ask
        ask_size = self.market[self.symbol].ask_size

        size = max(
            self._private_connectors[BybitAccountType.ALL_TESTNET]
            ._market[self.symbol]
            .limits.amount.min,
            min(ask_size, self.amount - self.pos),
        )
        amount = self.amount_to_precision(
            account_type=BybitAccountType.ALL_TESTNET,
            symbol=self.symbol,
            amount=size,
        )

        price = self.price_to_precision(
            account_type=BybitAccountType.ALL_TESTNET,
            symbol=self.symbol,
            price=ask,
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
            strategy_id="strategy_twap",
            user_id="test_user",
        )

        demo = Demo()
        demo.add_public_connector(conn_linear)
        demo.add_private_connector(private_conn)
        await demo.subscribe_bookl1(BybitAccountType.LINEAR_TESTNET, "BTC/USDT:USDT")
        await demo.run()

    except asyncio.CancelledError:
        print("Cancelled")
    finally:
        await conn_linear.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
