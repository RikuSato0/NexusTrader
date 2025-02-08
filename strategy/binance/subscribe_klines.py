from nexustrader.constants import settings
from nexustrader.config import Config, PublicConnectorConfig, PrivateConnectorConfig, BasicConfig
from nexustrader.strategy import Strategy
from nexustrader.constants import ExchangeType, KlineInterval
from nexustrader.exchange.binance import BinanceAccountType
from nexustrader.schema import Kline
from nexustrader.engine import Engine



BINANCE_API_KEY = settings.BINANCE.FUTURE.TESTNET_1.api_key
BINANCE_SECRET = settings.BINANCE.FUTURE.TESTNET_1.secret



class Demo(Strategy):
    def __init__(self):
        super().__init__()
    
    def on_start(self):
        self.subscribe_kline(symbols=["BTCUSDT-PERP.BINANCE"], interval=KlineInterval.MINUTE_1)
        
    def on_kline(self, kline: Kline):
        print(kline)
        

config = Config(
    strategy_id="subscribe_klines_binance",
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
    }
)

engine = Engine(config)

if __name__ == "__main__":
    try:
        engine.start()
    finally:
        engine.dispose()
