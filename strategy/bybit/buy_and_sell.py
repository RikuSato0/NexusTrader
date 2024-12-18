from decimal import Decimal

from tradebot.constants import KEYS
from tradebot.config import Config, PublicConnectorConfig, PrivateConnectorConfig, BasicConfig
from tradebot.strategy import Strategy
from tradebot.constants import ExchangeType, OrderSide, OrderType
from tradebot.exchange.bybit import BybitAccountType
from tradebot.schema import BookL1, Order
from tradebot.engine import Engine

BYBIT_API_KEY = KEYS["bybit_testnet_2"]["API_KEY"]
BYBIT_SECRET = KEYS["bybit_testnet_2"]["SECRET"]




class Demo(Strategy):
    def __init__(self):
        super().__init__()
        self.subscribe_bookl1(symbols=["BTCUSDT-PERP.BYBIT"])
        self.subscribe_trade(symbols=["BTCUSDT-PERP.BYBIT"])
        
        self.schedule(self.algo, seconds=1)
        self.signal = True
        self.uuid = None
    
    def algo(self):
        bookl1 = self.cache.bookl1("BTCUSDT-PERP.BYBIT")
        if bookl1:
            if self.signal:
                order = self.create_order(
                    symbol="BTCUSDT-PERP.BYBIT",
                    side=OrderSide.BUY,
                    type=OrderType.MARKET,
                    amount=Decimal("0.001"),
                )
                print(order.uuid)
                self.uuid = order.uuid
                self.signal = False
            if self.uuid:
                order = self.cache.get_order(self.uuid)
                print(order)

config = Config(
    strategy_id="buy_and_sell",
    user_id="user_test",
    strategy=Demo(),
    basic_config={
        ExchangeType.BYBIT: BasicConfig(
            api_key=BYBIT_API_KEY,
            secret=BYBIT_SECRET,
            testnet=True,
        )
    },
    public_conn_config={
        ExchangeType.BYBIT: [
            PublicConnectorConfig(
                account_type=BybitAccountType.LINEAR_TESTNET,
            ),
            PublicConnectorConfig(
                account_type=BybitAccountType.SPOT_TESTNET,
            ),
        ]
    },
    private_conn_config={
        ExchangeType.BYBIT: [
            PrivateConnectorConfig(
                account_type=BybitAccountType.ALL_TESTNET,
            )
        ]
    }
)

engine = Engine(config)

if __name__ == "__main__":
    try:
        engine.start()
    finally:
        engine.dispose()
