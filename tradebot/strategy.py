from typing import Dict, List, Set
from decimal import Decimal
from tradebot.core.log import SpdLog
from tradebot.base import TaskManager
from tradebot.core.oms import OrderExecutionSystem
from tradebot.core.nautilius_core import MessageBus
from tradebot.schema import BookL1, Trade, Kline, Order, MarketData, OrderSubmit
from tradebot.constants import DataType, OrderSide, OrderType, TimeInForce, PositionSide, AccountType


class Strategy:
    def __init__(self):
        self.log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )

        self._subscriptions: Dict[DataType, Dict[str, str] | Set[str]] = {
            DataType.BOOKL1: set(),
            DataType.TRADE: set(),
            DataType.KLINE: {},
        }

        self._market_data: MarketData = MarketData()

        self._initialized = False

    def _init_core(
        self, msgbus: MessageBus, task_manager: TaskManager, oes: OrderExecutionSystem
    ):
        if self._initialized:
            return

        self._oes = oes
        self._task_manager = task_manager
        self._msgbus = msgbus
        self._msgbus.register(endpoint="trade", handler=self.on_trade)
        self._msgbus.register(endpoint="bookl1", handler=self.on_bookl1)
        self._msgbus.register(endpoint="kline", handler=self.on_kline)
        self._msgbus.register(endpoint="accepted", handler=self.on_accepted_order)
        self._msgbus.register(
            endpoint="partially_filled", handler=self.on_partially_filled_order
        )
        self._msgbus.register(endpoint="filled", handler=self.on_filled_order)
        self._msgbus.register(endpoint="canceled", handler=self.on_canceled_order)
        self._msgbus.register(endpoint="failed", handler=self.on_failed_order)
        self._msgbus.register(endpoint="pending", handler=self.on_pending_order)
        self._initialized = True

    def create_order(
        self,
        symbol: str,
        side: OrderSide,
        type: OrderType,
        amount: Decimal,
        price: Decimal | None = None,
        time_in_force: TimeInForce | None = None,
        position_side: PositionSide | None = None,
        account_type: AccountType | None = None,
        **kwargs,
    ):
        order = OrderSubmit(
            symbol=symbol,
            side=side,
            type=type,
            amount=amount,
            price=price,
            time_in_force=time_in_force,
            position_side=position_side,
            kwargs=kwargs,
        )
        self._oes._submit_order(order, account_type)
    
    def cancel_order(self, symbol: str, order_id: str | int, account_type: AccountType | None = None, **kwargs):
        order = OrderSubmit(
            symbol=symbol,
            order_id=order_id,
            kwargs=kwargs,
        )
        self._oes._submit_cancel_order(order, account_type)

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
    
    def on_pending_order(self, order: Order):
        pass

    def on_accepted_order(self, order: Order):
        pass

    def on_partially_filled_order(self, order: Order):
        pass

    def on_filled_order(self, order: Order):
        pass

    def on_canceled_order(self, order: Order):
        pass

    def on_failed_order(self, order: Order):
        pass
    