import zmq
from zmq.asyncio import Context
from decimal import Decimal
from tradebot.constants import settings
from tradebot.config import Config, PublicConnectorConfig, PrivateConnectorConfig, BasicConfig, ZeroMQSignalConfig
from tradebot.strategy import Strategy
from tradebot.constants import ExchangeType, OrderSide
from tradebot.exchange.bybit import BybitAccountType
from tradebot.schema import BookL1, Order
from tradebot.engine import Engine


BYBIT_API_KEY = settings.BYBIT.ACCOUNT1.api_key
BYBIT_SECRET = settings.BYBIT.ACCOUNT1.secret

context = Context()
socket = context.socket(zmq.SUB)
socket.connect("ipc:///tmp/zmq_data_test")
socket.setsockopt(zmq.SUBSCRIBE, b"")

class Demo(Strategy):
    def __init__(self):
        super().__init__()
        self.subscribe_bookl1(symbols=["BTCUSDT-PERP.BYBIT"])
        self.signal = True
        
    def on_custom_signal(self, signal):
        print(signal)
        

config = Config(
    strategy_id="bybit_twap",
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
                account_type=BybitAccountType.UNIFIED_TESTNET,
            )
        ]
    },
    zero_mq_signal_config=ZeroMQSignalConfig(
        socket=socket,
    )
)

engine = Engine(config)

if __name__ == "__main__":
    try:
        engine.start()
    finally:
        engine.dispose()
