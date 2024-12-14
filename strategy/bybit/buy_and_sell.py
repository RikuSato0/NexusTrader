from tradebot.constants import KEYS
from tradebot.config import Config, PublicConnectorConfig, PrivateConnectorConfig, BasicConfig
from tradebot.strategy import Strategy
from tradebot.constants import ExchangeType
from tradebot.exchange.bybit import BybitAccountType
from tradebot.exchange.binance import BinanceAccountType
from tradebot.types import BookL1
from tradebot.engine import Engine

BYBIT_API_KEY = KEYS["bybit_testnet_2"]["API_KEY"]
BYBIT_SECRET = KEYS["bybit_testnet_2"]["SECRET"]

BINANCE_API_KEY = KEYS["binance_future_testnet"]["API_KEY"]
BINANCE_SECRET = KEYS["binance_future_testnet"]["SECRET"]


class Demo(Strategy):
    def __init__(self):
        super().__init__()
        self.subscribe_bookl1(symbols=["BTCUSDT-PERP.BYBIT", "ETHUSDT-PERP.BYBIT"])
        self.subscribe_bookl1(symbols=["BTCUSDT.BYBIT", "ETHUSDT.BYBIT"])
        self.subscribe_bookl1(symbols=["BTCUSDT-PERP.BINANCE", "ETHUSDT-PERP.BINANCE"])
    
    def on_bookl1(self, data: BookL1):
        print(data)

config = Config(
    strategy_id="buy_and_sell",
    user_id="user_test",
    strategy=Demo(),
    basic_config={
        ExchangeType.BYBIT: BasicConfig(
            api_key=BYBIT_API_KEY,
            secret=BYBIT_SECRET,
            testnet=True,
        ),
        ExchangeType.BINANCE: BasicConfig(
            api_key=BINANCE_API_KEY,
            secret=BINANCE_SECRET,
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
        ],
        ExchangeType.BINANCE: [
            PublicConnectorConfig(
                account_type=BinanceAccountType.USD_M_FUTURE_TESTNET,
            ),
        ]
    },
    private_conn_config={
        ExchangeType.BYBIT: [
            PrivateConnectorConfig(
                account_type=BybitAccountType.ALL_TESTNET,
            )
        ],
        ExchangeType.BINANCE: [
            PrivateConnectorConfig(
                account_type=BinanceAccountType.USD_M_FUTURE_TESTNET,
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
