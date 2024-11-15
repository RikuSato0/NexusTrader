import asyncio
from typing import Dict
from decimal import Decimal
from typing import Literal
from tradebot.log import SpdLog
from tradebot.constants import EventType, AccountType, OrderStatus
from tradebot.base import Clock, PublicConnector, PrivateConnector
from tradebot.entity import EventSystem
from tradebot.types import BookL1, Trade, Kline, Order, MarketData
from tradebot.constants import OrderSide, OrderType, TimeInForce, PositionSide


class Strategy:
    def __init__(self, tick_size=0.01):
        self.log = SpdLog.get_logger(name = type(self).__name__, level = "DEBUG", flush = True)
        self._pulic_connectors: Dict[AccountType, PublicConnector] = {}
        self._private_connectors: Dict[AccountType, PrivateConnector] = {}
        self._clock = Clock(tick_size=tick_size)
        self._market_data: MarketData = MarketData()
        self._clock.add_tick_callback(self._on_tick)
        EventSystem.on(EventType.TRADE, self._on_trade)
        EventSystem.on(EventType.BOOKL1, self._on_bookl1)
        EventSystem.on(EventType.KLINE, self._on_kline)
        EventSystem.on(OrderStatus.ACCEPTED, self._on_accepted_order)
        EventSystem.on(OrderStatus.PARTIALLY_FILLED, self._on_partially_filled_order)
        EventSystem.on(OrderStatus.FILLED, self._on_filled_order)
        EventSystem.on(OrderStatus.CANCELED, self._on_canceled_order)
    
    
    def market(self, account_type: AccountType):
        return self._private_connectors[account_type]._market
    
    def cache(self, account_type: AccountType):
        return self._private_connectors[account_type]._cache

    async def create_order(
        self,
        account_type: AccountType,
        symbol: str,
        side: OrderSide,
        type: OrderType,
        amount: Decimal,
        price: Decimal = None,
        time_in_force: TimeInForce = TimeInForce.GTC,
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

    async def cancel_order(
        self, account_type: AccountType, symbol: str, order_id: str, **kwargs
    ):
        params = {
            "symbol": symbol,
            "order_id": order_id,
        }
        params.update(kwargs)
        return await self._private_connectors[account_type].cancel_order(**params)

    def price_to_precision(
        self,
        account_type: AccountType,
        symbol: str,
        price: float,
        mode: Literal["round", "ceil", "floor"] = "round",
    ) -> Decimal:
        return self._private_connectors[account_type].price_to_precision(
            symbol, price, mode
        )

    def amount_to_precision(
        self,
        account_type: AccountType,
        symbol: str,
        amount: float,
        mode: Literal["round", "ceil", "floor"] = "round",
    ) -> Decimal:
        return self._private_connectors[account_type].amount_to_precision(
            symbol, amount, mode
        )

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
        for private_connector in self._private_connectors.values():
            await private_connector.connect()
        await asyncio.sleep(5)
        await self._clock.run()

    def _on_accepted_order(self, order: Order):
        if hasattr(self, "on_accepted_order"):
            self.on_accepted_order(order)

    def _on_partially_filled_order(self, order: Order):
        if hasattr(self, "on_partially_filled_order"):
            self.on_partially_filled_order(order)

    def _on_filled_order(self, order: Order):
        if hasattr(self, "on_filled_order"):
            self.on_filled_order(order)

    def _on_canceled_order(self, order: Order):
        if hasattr(self, "on_canceled_order"):
            self.on_canceled_order(order)

    def get_bookl1(self, exchange: str, symbol: str):
        return self._market_data.bookl1[exchange][symbol]
    
    def get_trade(self, exchange: str, symbol: str):
        return self._market_data.trade[exchange][symbol]

    def _on_trade(self, trade: Trade):
        self._market_data.update_trade(trade)
        if hasattr(self, "on_trade"):
            self.on_trade(trade)

    def _on_bookl1(self, bookl1: BookL1):
        self._market_data.update_bookl1(bookl1)
        if hasattr(self, "on_bookl1"):
            self.on_bookl1(bookl1)

    def _on_kline(self, kline: Kline):
        self._market_data.update_kline(kline)
        if hasattr(self, "on_kline"):
            self.on_kline(kline)

    async def _on_tick(self, tick):
        if hasattr(self, "on_tick"):
            await self.on_tick(tick)
