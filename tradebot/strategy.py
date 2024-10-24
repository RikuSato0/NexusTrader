from typing import Dict

from tradebot.constants import EventType, PublicConnectorType
from tradebot.base import Clock, PublicConnector
from tradebot.entity import EventSystem
from tradebot.types import BookL1, Trade, Kline


class Strategy:
    def __init__(self, tick_size=0.01):
        self._pulic_connectors: Dict[PublicConnectorType, PublicConnector] = {}
        self._clock = Clock(tick_size=tick_size)
        self._clock.add_tick_callback(self._on_tick)
        EventSystem.on(EventType.TRADE, self._on_trade)
        EventSystem.on(EventType.BOOKL1, self._on_bookl1)
        EventSystem.on(EventType.KLINE, self._on_kline)
        
    def add_public_connector(self, connector: PublicConnector):
        self._pulic_connectors[connector.account_type] = connector
        
    def add_private_connector(self, connector):
        #TODO: implement private connector
        pass
    
    async def subscribe_bookl1(self, type, symbol: str):
        await self._pulic_connectors[type].subscribe_bookl1(symbol)
    
    async def subscribe_trade(self, type, symbol: str):
        await self._pulic_connectors[type].subscribe_trade(symbol)
    
    async def subscribe_kline(self, type, symbol: str, interval: str):
        await self._pulic_connectors[type].subscribe_kline(symbol, interval)
        
    async def run(self):
        await self._clock.run()
    
    def _on_trade(self, trade: Trade):
        if hasattr(self, "on_trade"):
            self.on_trade(trade)
    
    def _on_bookl1(self, bookl1: BookL1):
        if hasattr(self, "on_bookl1"):
            self.on_bookl1(bookl1)
    
    def _on_kline(self, kline: Kline):
        if hasattr(self, "on_kline"):
            self.on_kline(kline)
    
    def _on_tick(self, tick):
        if hasattr(self, "on_tick"):
            self.on_tick(tick)
    
    
