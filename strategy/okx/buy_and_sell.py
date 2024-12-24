from decimal import Decimal

from tradebot.constants import settings
from tradebot.config import Config, PublicConnectorConfig, PrivateConnectorConfig, BasicConfig
from tradebot.strategy import Strategy
from tradebot.constants import ExchangeType, OrderSide, OrderType
from tradebot.exchange.okx import OkxAccountType
from tradebot.schema import BookL1, Order
from tradebot.engine import Engine



OKX_API_KEY = settings.OKX.DEMO_1.api_key
OKX_SECRET = settings.OKX.DEMO_1.secret
OKX_PASSPHRASE = settings.OKX.DEMO_1.passphrase



class Demo(Strategy):
    def __init__(self):
        super().__init__()
        self.subscribe_bookl1(symbols=["BTCUSDT.OKX"])
        self.signal = True
    
    def on_failed_order(self, order: Order):
        print(order)
    
    def on_pending_order(self, order: Order):
        print(order)
    
    def on_accepted_order(self, order: Order):
        print(order)
    
    def on_partially_filled_order(self, order: Order):
        print(order)
    
    def on_filled_order(self, order: Order):
        print(order)
    
    def on_bookl1(self, bookl1: BookL1):
        if self.signal:
            self.create_order(
                symbol="BTCUSDT.OKX",
                side=OrderSide.BUY,
                type=OrderType.MARKET,
                amount=Decimal("0.01"),
            )
            self.create_order(
                symbol="BTCUSDT.OKX",
                side=OrderSide.SELL,
                type=OrderType.MARKET,
                amount=Decimal("0.01"),
            )
            self.signal = False
        

config = Config(
    strategy_id="okx_buy_and_sell",
    user_id="user_test",
    strategy=Demo(),
    basic_config={
        ExchangeType.OKX: BasicConfig(
            api_key=OKX_API_KEY,
            secret=OKX_SECRET,
            passphrase=OKX_PASSPHRASE,
            testnet=True,
        )
    },
    public_conn_config={
        ExchangeType.OKX: [
            PublicConnectorConfig(
                account_type=OkxAccountType.DEMO,
            )
        ]
    },
    private_conn_config={
        ExchangeType.OKX: [
            PrivateConnectorConfig(
                account_type=OkxAccountType.DEMO,
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
