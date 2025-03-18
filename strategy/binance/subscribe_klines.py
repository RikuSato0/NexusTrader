from nexustrader.constants import settings
from nexustrader.config import Config, PublicConnectorConfig, PrivateConnectorConfig, BasicConfig
from nexustrader.strategy import Strategy
from nexustrader.constants import ExchangeType, KlineInterval
from nexustrader.exchange.binance import BinanceAccountType
from nexustrader.schema import Kline
from nexustrader.engine import Engine
from nexustrader.core.log import SpdLog

SpdLog.initialize(level="DEBUG", std_level="ERROR", production_mode=True)


BINANCE_API_KEY = settings.BINANCE.LIVE.ACCOUNT1.API_KEY
BINANCE_SECRET = settings.BINANCE.LIVE.ACCOUNT1.SECRET



class Demo(Strategy):
    def __init__(self):
        super().__init__()
    
    def on_start(self):
        symbols = self.linear_info(exchange=ExchangeType.BINANCE, quote="USDT")
        self.subscribe_kline(symbols=symbols, interval=KlineInterval.MINUTE_1)
        self.subscribe_bookl1(symbols=symbols)
        
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
            testnet=False,
        )
    },
    public_conn_config={
        ExchangeType.BINANCE: [
            PublicConnectorConfig(
                account_type=BinanceAccountType.USD_M_FUTURE,
            )
        ]
    },
    private_conn_config={
        ExchangeType.BINANCE: [
            PrivateConnectorConfig(
                account_type=BinanceAccountType.USD_M_FUTURE,
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
