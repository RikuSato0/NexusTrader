import zmq
import orjson
from zmq.asyncio import Context
from decimal import Decimal
from tradebot.constants import settings
from tradebot.config import Config, PublicConnectorConfig, PrivateConnectorConfig, BasicConfig, ZeroMQSignalConfig
from tradebot.strategy import Strategy
from tradebot.constants import ExchangeType, OrderSide
from tradebot.exchange.bybit import BybitAccountType
from tradebot.schema import BookL1, Order
from tradebot.engine import Engine
from tradebot.core.entity import RateLimit, DataReady


BYBIT_API_KEY = settings.BYBIT.ACCOUNT1.api_key
BYBIT_SECRET = settings.BYBIT.ACCOUNT1.secret

context = Context()
socket = context.socket(zmq.SUB)
socket.connect("ipc:///tmp/zmq_data_test")
socket.setsockopt(zmq.SUBSCRIBE, b"")

class Demo(Strategy):
    def __init__(self):
        super().__init__()
        symbols = ["BTCUSDT-PERP.BYBIT"]
        self.subscribe_bookl1(symbols=symbols)
        self.signal = True
        self.multiplier = 0.1
        self.data_ready = DataReady(symbols=symbols)
        self.orders = {}
        
    def on_bookl1(self, bookl1: BookL1):
        self.data_ready.input(bookl1)
    
    
    def cal_diff(self, symbol, target_position) -> Decimal:
        position = self.cache.get_position(symbol).value_or(None)
        target_position = self.amount_to_precision(symbol, target_position)
        if position:
            diff = target_position - position.signed_amount
            self.log.debug(f"symbol: {symbol}, current {position.signed_amount} -> target {target_position}")
        else:
            diff = target_position
            self.log.debug(f"symbol: {symbol}, current 0 -> target {diff}")
        return diff
    
        
    def on_custom_signal(self, signal):
        signal = orjson.loads(signal)
        for pos in signal:
            if not self.data_ready.ready:
                self.log.debug("Data not ready, skip")
                continue
            
            symbol = pos["instrumentID"].replace("USDT.BBP", "USDT-PERP.BYBIT")
            target_position = pos["position"] * self.market(symbol).precision.amount * self.multiplier
            uuid = self.orders.get(symbol, None)

            if uuid:
                order = self.cache.get_order(uuid)
                is_opened = order.bind_optional(lambda order: order.is_opened).value_or(False)
                if is_opened:
                    self.cancel_twap(
                        symbol=symbol,
                        uuid=uuid,
                        account_type=BybitAccountType.UNIFIED_TESTNET,
                    )
                    self.log.debug(f"symbol: {symbol}, canceled {uuid}")
                uuid = None
            
            if uuid is None:
                diff = self.cal_diff(symbol, target_position)
                uuid = self.create_twap(
                    symbol=symbol,
                    side=OrderSide.BUY if diff > 0 else OrderSide.SELL,
                    amount=abs(diff),
                    duration=65,
                    wait=5,
                    account_type=BybitAccountType.UNIFIED_TESTNET, # recommend to specify the account type
                )
                
                self.orders[symbol] = uuid
                    
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
                rate_limit=RateLimit(
                    max_rate=20,
                    time_period=1,
                )
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
