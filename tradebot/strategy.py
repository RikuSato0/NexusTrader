from typing import Dict

from tradebot.constants import WSType, EventType
from tradebot.base import WSManager, Clock
from tradebot.entity import EventSystem
from tradebot.types import BookL1, Trade, Kline


class Strategy:
    def __init__(self):
        self._ws_manager: Dict[WSType, WSManager] = {}
        self._clock = Clock(tick_size=0.01)
        self._clock.add_tick_callback(self._on_tick)
        EventSystem.on(EventType.TRADE, self._on_trade)
        EventSystem.on(EventType.BOOKL1, self._on_book_l1)
        EventSystem.on(EventType.KLINE, self._on_kline)
        
    def add_ws_manager(self, ws_type: WSType, ws_manager: WSManager):
        self._ws_manager[ws_type] = ws_manager
    
    async def subscribe_book_l1(self, ws_type: WSType, symbol: str):
        await self._ws_manager[ws_type].subscribe_book_l1(symbol)
    
    async def subscribe_trade(self, ws_type: WSType, symbol: str):
        await self._ws_manager[ws_type].subscribe_trade(symbol)
    
    async def subscribe_kline(self, ws_type: WSType, symbol: str, interval: str):
        await self._ws_manager[ws_type].subscribe_kline(symbol, interval)
    
    def _on_trade(self, trade: Trade):
        if hasattr(self, "on_trade"):
            self.on_trade(trade)
    
    def _on_book_l1(self, book_l1: BookL1):
        if hasattr(self, "on_book_l1"):
            self.on_book_l1(book_l1)
    
    def _on_kline(self, kline: Kline):
        if hasattr(self, "on_kline"):
            self.on_kline(kline)
    
    def _on_tick(self, tick):
        if hasattr(self, "on_tick"):
            self.on_tick(tick)
