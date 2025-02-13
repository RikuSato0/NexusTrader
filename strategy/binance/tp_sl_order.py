from decimal import Decimal

from nexustrader.constants import settings
from nexustrader.config import (
    Config,
    PublicConnectorConfig,
    PrivateConnectorConfig,
    BasicConfig,
)
from nexustrader.strategy import Strategy
from nexustrader.constants import ExchangeType, OrderSide, OrderType
from nexustrader.exchange.binance import BinanceAccountType
from nexustrader.schema import BookL1, Order
from nexustrader.engine import Engine


BINANCE_API_KEY = settings.BINANCE.FUTURE.TESTNET_1.API_KEY
BINANCE_SECRET = settings.BINANCE.FUTURE.TESTNET_1.SECRET


class Demo(Strategy):
    def __init__(self):
        super().__init__()
        self.signal = True

    def on_start(self):
        self.subscribe_bookl1(symbols=["BTCUSDT-PERP.BINANCE"])

    def on_canceled_order(self, order: Order):
        print(order, "\n")

    def on_failed_order(self, order: Order):
        print(order, "\n")

    def on_partially_filled_order(self, order: Order):
        print(order, "\n")

    def on_pending_order(self, order: Order):
        print(order, "\n")

    def on_accepted_order(self, order: Order):
        print(order, "\n")

    def on_filled_order(self, order: Order):
        print(order, "\n")

    def on_bookl1(self, bookl1: BookL1):
        if self.signal:
            self.create_order(
                symbol="BTCUSDT-PERP.BINANCE",
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                amount=Decimal("0.01"),
            )

            bid_price = bookl1.bid
            trigger_price_tp = self.price_to_precision(
                symbol="BTCUSDT-PERP.BINANCE", price=bid_price * 1.009
            )  # trigger price is the price at which the order will be triggered
            tp = self.price_to_precision(
                symbol="BTCUSDT-PERP.BINANCE", price=bid_price * 1.01
            )  # price is the price at which the order will be filled
            trigger_price_sl = self.price_to_precision(
                symbol="BTCUSDT-PERP.BINANCE", price=bid_price * 0.991
            )  # trigger price is the price at which the order will be triggered
            sl = self.price_to_precision(
                symbol="BTCUSDT-PERP.BINANCE", price=bid_price * 0.99
            )  # price is the price at which the order will be filled
            uuid_tp = self.create_order(
                symbol="BTCUSDT-PERP.BINANCE",
                side=OrderSide.SELL,
                type=OrderType.TAKE_PROFIT_LIMIT,
                amount=Decimal("0.01"),
                trigger_price=trigger_price_tp,
                price=tp,
                reduce_only=True,
            )
            print(uuid_tp)

            self.cancel_order(symbol="BTCUSDT-PERP.BINANCE", uuid=uuid_tp)

            uuid_sl = self.create_order(
                symbol="BTCUSDT-PERP.BINANCE",
                side=OrderSide.SELL,
                type=OrderType.STOP_LOSS_LIMIT,
                amount=Decimal("0.01"),
                trigger_price=trigger_price_sl,
                price=sl,
                reduce_only=True,
            )
            print(uuid_sl)
            self.signal = False


config = Config(
    strategy_id="tp_sl_order",
    user_id="user_test",
    strategy=Demo(),
    basic_config={
        ExchangeType.BINANCE: BasicConfig(
            api_key=BINANCE_API_KEY,
            secret=BINANCE_SECRET,
            testnet=True,
        )
    },
    public_conn_config={
        ExchangeType.BINANCE: [
            PublicConnectorConfig(
                account_type=BinanceAccountType.USD_M_FUTURE_TESTNET,
            )
        ]
    },
    private_conn_config={
        ExchangeType.BINANCE: [
            PrivateConnectorConfig(
                account_type=BinanceAccountType.USD_M_FUTURE_TESTNET,
            )
        ]
    },
)

engine = Engine(config)

if __name__ == "__main__":
    try:
        engine.start()
    finally:
        engine.dispose()
