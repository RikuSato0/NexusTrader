import zmq
from tradebot.constants import KEYS
from tradebot.config import Config, PublicConnectorConfig, PrivateConnectorConfig, BasicConfig, ZeroMQSignalConfig
from tradebot.strategy import Strategy
from tradebot.constants import ExchangeType
from tradebot.exchange.bybit import BybitAccountType
from tradebot.schema import BookL1, Order
from tradebot.engine import Engine
from zmq.asyncio import Context

BYBIT_API_KEY = KEYS["bybit_testnet_2"]["API_KEY"]
BYBIT_SECRET = KEYS["bybit_testnet_2"]["SECRET"]

context = Context()
socket = context.socket(zmq.SUB)
socket.connect("ipc:///tmp/zmq_data_test")
socket.setsockopt(zmq.SUBSCRIBE, b"")


class Demo(Strategy):
    def __init__(self):
        super().__init__()
        self.subscribe_bookl1(symbols=["BTCUSDT-PERP.BYBIT"])
        self.subscribe_trade(symbols=["BTCUSDT-PERP.BYBIT"])
    
    def on_bookl1(self, bookl1: BookL1):
        print(bookl1)

    
    async def on_custom_signal(self, signal: bytes):
        print(signal)
    

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
