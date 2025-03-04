import pandas as pd
from nexustrader.core.entity import RateLimit
from nexustrader.constants import settings
from nexustrader.config import Config, PublicConnectorConfig, PrivateConnectorConfig, BasicConfig
from nexustrader.strategy import Strategy
from nexustrader.constants import ExchangeType, KlineInterval
from nexustrader.exchange.okx import OkxAccountType
from nexustrader.engine import Engine
from nexustrader.schema import Kline


OKX_API_KEY = settings.OKX.DEMO_1.API_KEY
OKX_SECRET = settings.OKX.DEMO_1.SECRET
OKX_PASSPHRASE = settings.OKX.DEMO_1.PASSPHRASE



class Demo(Strategy):
    def __init__(self):
        super().__init__()
        self.signal = True
    
    def on_start(self):
        end = self.clock.timestamp_ms()
        self.subscribe_bookl1(symbols=["BTCUSDT.OKX"])
        klines: list[Kline] = self.request_klines(
            symbol="BTCUSDT.OKX",
            account_type=OkxAccountType.DEMO,
            interval=KlineInterval.MINUTE_1,
            limit=300,
            end_time=end,
        )
        data = {
            "timestamp": [kline.start for kline in klines],
            "open": [kline.open for kline in klines],
            "high": [kline.high for kline in klines],
            "low": [kline.low for kline in klines],
            "close": [kline.close for kline in klines],
            "volume": [kline.volume for kline in klines],
        }
        df = pd.DataFrame(data)
        print(df)
    
        

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
                rate_limit=RateLimit(
                    max_rate=20,
                    time_period=1,
                )
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
