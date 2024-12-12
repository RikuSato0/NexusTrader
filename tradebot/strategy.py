from typing import Dict, List, Set
from tradebot.core.log import SpdLog
from tradebot.base import TaskManager
from tradebot.core.nautilius_core import MessageBus
from tradebot.types import BookL1, Trade, Kline, Order, MarketData
from tradebot.constants import DataType


class Strategy:
    def __init__(self):
        self.log = SpdLog.get_logger(name = type(self).__name__, level = "DEBUG", flush = True)

        self._subscriptions: Dict[DataType, Dict[str, str] | Set[str]] = {
            DataType.BOOKL1: set(),
            DataType.TRADE: set(),
            DataType.KLINE: {},
        }
        
        self._market_data: MarketData = MarketData()
        
        self._initialized = False
    
    def _init_core(self, msgbus: MessageBus, task_manager: TaskManager):
        if self._initialized:
            return
        
        self._task_manager = task_manager
        self._msgbus = msgbus
        self._msgbus.register(endpoint="trade", handler=self.on_trade)
        self._msgbus.register(endpoint="bookl1", handler=self.on_bookl1)
        self._msgbus.register(endpoint="kline", handler=self.on_kline)
        self._msgbus.register(endpoint="accepted", handler=self.on_accepted_order)
        self._msgbus.register(endpoint="partially_filled", handler=self.on_partially_filled_order)
        self._msgbus.register(endpoint="filled", handler=self.on_filled_order)
        self._msgbus.register(endpoint="canceled", handler=self.on_canceled_order)
        
        self._initialized = True
                
    
    def subscribe_bookl1(self, symbols: List[str]):
        for symbol in symbols:
            self._subscriptions[DataType.BOOKL1].add(symbol)
        
    def subscribe_trade(self, symbols: List[str]):
        for symbol in symbols:
            self._subscriptions[DataType.TRADE].add(symbol)
    
    def subscribe_kline(self, symbols: List[str], interval: str):
        for symbol in symbols:
            self._subscriptions[DataType.KLINE][symbol] = interval
        
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
