from typing import Dict
from decimal import Decimal
from tradebot.constants import EventType, AccountType, OrderStatus
from tradebot.base import Clock, PublicConnector, PrivateConnector
from tradebot.entity import EventSystem
from tradebot.types import BookL1, Trade, Kline, Order
from tradebot.constants import OrderSide, OrderType, TimeInForce, PositionSide

class Strategy:
    def __init__(self, tick_size=0.01):
        self._pulic_connectors: Dict[AccountType, PublicConnector] = {}
        self._private_connectors: Dict[AccountType, PrivateConnector] = {}
        self._clock = Clock(tick_size=tick_size)
        self._clock.add_tick_callback(self._on_tick)
        EventSystem.on(EventType.TRADE, self._on_trade)
        EventSystem.on(EventType.BOOKL1, self._on_bookl1)
        EventSystem.on(EventType.KLINE, self._on_kline)
        # EventSystem.on(OrderStatus.NEW, self._on_new_order)
        # EventSystem.on(OrderStatus.PARTIALLY_FILLED, self._on_partially_filled_order)
        # EventSystem.on(OrderStatus.FILLED, self._on_filled_order)
        # EventSystem.on(OrderStatus.CANCELED, self._on_canceled_order)

    async def create_order(
        self,
        account_type: AccountType,
        symbol: str,
        side: OrderSide,
        type: OrderType,
        amount: Decimal,
        price: Decimal = None,
        time_in_force: TimeInForce = None,
        position_side: PositionSide = None,
        **kwargs,
    ):
        params = {
            "symbol": symbol,
            "side": side,
            "type": type,
            "amount": amount,
            "price": price,
            "time_in_force": time_in_force,
            "position_side": position_side,
        }
        params.update(kwargs)
        return await self._private_connectors[account_type].create_order(**params)
    
    async def cancel_order(self, account_type: AccountType, symbol: str, order_id: str, **kwargs):
        params = {
            "symbol": symbol,
            "order_id": order_id,
        }
        params.update(kwargs)
        return await self._private_connectors[account_type].cancel_order(**params)
        
        

    def add_public_connector(self, connector: PublicConnector):
        self._pulic_connectors[connector.account_type] = connector

    def add_private_connector(self, connector: PrivateConnector):
        self._private_connectors[connector.account_type] = connector

    async def subscribe_bookl1(self, type: AccountType, symbol: str):
        await self._pulic_connectors[type].subscribe_bookl1(symbol)

    async def subscribe_trade(self, type: AccountType, symbol: str):
        await self._pulic_connectors[type].subscribe_trade(symbol)

    async def subscribe_kline(self, type: AccountType, symbol: str, interval: str):
        await self._pulic_connectors[type].subscribe_kline(symbol, interval)

    async def run(self):
        await self._clock.run()

    def _on_new_order(self, order: Order):
        if hasattr(self, "on_new_order"):
            self.on_new_order(order)

    def _on_partially_filled_order(self, order: Order):
        if hasattr(self, "on_partially_filled_order"):
            self.on_partially_filled_order(order)

    def _on_filled_order(self, order: Order):
        if hasattr(self, "on_filled_order"):
            self.on_filled_order(order)

    def _on_canceled_order(self, order: Order):
        if hasattr(self, "on_canceled_order"):
            self.on_canceled_order(order)

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
