from typing import Dict, List, Set
from tradebot.core.log import SpdLog
from tradebot.constants import AccountType, ExchangeType, InstrumentType
from tradebot.base import PublicConnector, PrivateConnector, TaskManager
from tradebot.core.nautilius_core import MessageBus
from tradebot.types import BookL1, Trade, Kline, Order, MarketData, InstrumentId

from tradebot.exchange.bybit import BybitAccountType
from tradebot.exchange.binance import BinanceAccountType
from tradebot.exchange.okx import OkxAccountType

class Strategy:
    def __init__(self, msgbus: MessageBus, task_manager: TaskManager):
        self.log = SpdLog.get_logger(name = type(self).__name__, level = "DEBUG", flush = True)
        self._subscribed_symbols: Set[InstrumentId] = set()
        self._market_data: MarketData = MarketData()
        self._subscribed_pairs = set() # Store (exchange_id, symbol, data_type) tuples
        self._ready = False
        self._task_manager = task_manager
        self._msgbus = msgbus
        self._msgbus.register(endpoint="trade", handler=self.on_trade)
        self._msgbus.register(endpoint="bookl1", handler=self.on_bookl1)
        self._msgbus.register(endpoint="kline", handler=self.on_kline)
        self._msgbus.register(endpoint="accepted", handler=self.on_accepted_order)
        self._msgbus.register(endpoint="partially_filled", handler=self.on_partially_filled_order)
        self._msgbus.register(endpoint="filled", handler=self.on_filled_order)
        self._msgbus.register(endpoint="canceled", handler=self.on_canceled_order)
                
    
    def subscribe_bookl1(self, symbols: List[str]):
        pass
        
    def subscribe_trade(self, symbols: List[str]):
        pass
    
    def subscribe_kline(self, symbols: List[str], interval: str):
        pass
        
    def on_trade(self, trade: Trade):
        pass
    
    def on_bookl1(self, bookl1: BookL1):
        pass
    
    def on_kline(self, kline: Kline):
        pass
    
    def on_accepted_order(self, order: Order):
        pass
    
    def on_partially_filled_order(self, order: Order):
        pass
    
    def on_filled_order(self, order: Order):
        pass
    
    def on_canceled_order(self, order: Order):
        pass
