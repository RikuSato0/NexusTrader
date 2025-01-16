from decimal import Decimal
from typing import Dict, List, Tuple, Any
from typing import Optional
from msgspec import Struct, field
from nexustrader.core.nautilius_core import UUID4
from nexustrader.constants import (
    OrderSide,
    OrderType,
    TimeInForce,
    OrderStatus,
    PositionSide,
    InstrumentType,
    ExchangeType,
    SubmitType,
    AlgoOrderStatus,
)


class InstrumentId(Struct):
    symbol: str
    exchange: ExchangeType
    type: InstrumentType

    @property
    def is_spot(self) -> bool:
        return self.type == InstrumentType.SPOT

    @property
    def is_linear(self) -> bool:
        return self.type == InstrumentType.LINEAR

    @property
    def is_inverse(self) -> bool:
        return self.type == InstrumentType.INVERSE

    @classmethod
    def from_str(cls, symbol: str):
        """
        BTCETH.BINANCE -> SPOT
        BTCUSDT-PERP.BINANCE -> LINEAR
        BTCUSD.BINANCE -> INVERSE
        BTCUSD-241227.BINANCE
        """
        symbol_prefix, exchange = symbol.split(".")

        # if numirical number in id, then it is a future
        if "-" in symbol_prefix:
            prefix, _ = symbol_prefix.split("-")
            if prefix.endswith("USD"):
                type = InstrumentType.INVERSE
            else:
                type = InstrumentType.LINEAR
        else:
            type = InstrumentType.SPOT

        return cls(symbol=symbol, exchange=ExchangeType(exchange.lower()), type=type)


class BookL1(Struct, gc=False):
    exchange: ExchangeType
    symbol: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    timestamp: int


class BookL2(Struct):
    exchange: ExchangeType
    symbol: str
    bids: List[Tuple[float, float]]
    asks: List[Tuple[float, float]]
    timestamp: int


class Trade(Struct, gc=False):
    exchange: ExchangeType
    symbol: str
    price: float
    size: float
    timestamp: int


class Kline(Struct, gc=False):
    exchange: ExchangeType
    symbol: str
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: int


class MarkPrice(Struct, gc=False):
    exchange: ExchangeType
    symbol: str
    price: float
    timestamp: int


class FundingRate(Struct, gc=False):
    exchange: ExchangeType
    symbol: str
    rate: float
    timestamp: int
    next_funding_time: int


class IndexPrice(Struct, gc=False):
    exchange: ExchangeType
    symbol: str
    price: float
    timestamp: int


class OrderSubmit(Struct):
    symbol: str
    instrument_id: InstrumentId
    submit_type: SubmitType
    uuid: str = field(default_factory=lambda: UUID4().value)
    order_id: str | int | None = None
    side: OrderSide | None = None
    type: OrderType | None = None
    amount: Decimal | None = None
    price: Decimal | None = None
    time_in_force: TimeInForce | None = TimeInForce.GTC
    position_side: PositionSide | None = None
    duration: int | None = None
    wait: int | None = None
    kwargs: Dict[str, Any] = {}
    status: OrderStatus = OrderStatus.INITIALIZED


class Order(Struct):
    exchange: ExchangeType
    symbol: str
    status: OrderStatus
    id: Optional[str] = None
    uuid: Optional[str] = None
    amount: Optional[Decimal] = None
    filled: Optional[Decimal] = None
    client_order_id: Optional[str] = None
    timestamp: Optional[int] = None
    type: Optional[OrderType] = None
    side: Optional[OrderSide] = None
    time_in_force: Optional[TimeInForce] = None
    price: Optional[float] = None
    average: Optional[float] = None
    last_filled_price: Optional[float] = None
    last_filled: Optional[Decimal] = None
    remaining: Optional[Decimal] = None
    fee: Optional[Decimal] = None
    fee_currency: Optional[str] = None
    cost: Optional[Decimal] = None
    cum_cost: Optional[Decimal] = None
    reduce_only: Optional[bool] = None
    position_side: Optional[PositionSide] = None

    @property
    def success(self) -> bool:
        return self.status not in [OrderStatus.FAILED, OrderStatus.CANCEL_FAILED]

    @property
    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED

    @property
    def is_canceled(self) -> bool:
        return self.status == OrderStatus.CANCELED

    @property
    def is_closed(self) -> bool:
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
            OrderStatus.EXPIRED,
        ]

    @property
    def is_opened(self) -> bool:
        return self.status in [
            OrderStatus.PENDING,
            OrderStatus.CANCELING,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.ACCEPTED,
        ]
    
    @property
    def on_flight(self) -> bool:
        return self.status in [
            OrderStatus.PENDING,
            OrderStatus.CANCELING,
        ]


class AlgoOrder(Struct):
    symbol: str
    uuid: str # start with "ALGO-"
    side: OrderSide
    amount: Decimal
    duration: int
    wait: int
    status: AlgoOrderStatus
    exchange: ExchangeType
    timestamp: int 
    orders: List[str] = field(default_factory=list) # [uuid1, uuid2, ...]
    position_side: PositionSide | None = None
    
    @property
    def is_running(self) -> bool:
        return self.status == AlgoOrderStatus.RUNNING
    
    @property
    def is_finished(self) -> bool:
        return self.status == AlgoOrderStatus.FINISHED
    
    @property
    def is_canceled(self) -> bool:
        return self.status == AlgoOrderStatus.CANCELED
    
    @property
    def is_failed(self) -> bool:
        return self.status == AlgoOrderStatus.FAILED
    
    @property
    def is_closed(self) -> bool:
        return self.status in [AlgoOrderStatus.CANCELED, AlgoOrderStatus.FAILED, AlgoOrderStatus.FINISHED]
    
    @property
    def is_opened(self) -> bool:
        return self.status in [AlgoOrderStatus.RUNNING, AlgoOrderStatus.CANCELING]

class Balance(Struct):
    """
    Buy BTC/USDT: amount = 0.01, cost: 600

    OrderStatus.INITIALIZED: BTC(free: 0.0, locked: 0.0) USDT(free: 1000, locked: 0)
    OrderStatus.PENDING: BTC(free: 0.0, locked: 0) USDT(free: 400, locked: 600) USDT.update_locked(600) USDT.update_free(-600)

    OrderStatus.PARTIALLY_FILLED: BTC(free: 0.005, locked: 0) USDT(free: 400, locked: 300) BTC.update_free(0.005) USDT.update_locked(-300)
    OrderStatus.FILLED: BTC(free: 0.01, locked: 0.0) USDT(free: 400, locked: 0) BTC.update_free(0.005) USDT.update_locked(-300)

    Buy BTC/USDT: amount = 0.01, cost: 200

    OrderStatus.INITIALIZED: BTC(free: 0.01, locked: 0.0) USDT(free: 400, locked: 0)
    OrderStatus.PENDING: BTC(free: 0.01, locked: 0.0) USDT(free: 200, locked: 200) USDT.update_locked(200) USDT.update_free(-200)
    OrderStatus.FILLED: BTC(free: 0.02, locked: 0.0) USDT(free: 200, locked: 0) BTC.update_free(0.01) USDT.update_locked(-200)

    Sell BTC/USDT: amount = 0.01, cost: 300
    OrderStatus.INITIALIZED: BTC(free: 0.02, locked: 0.0) USDT(free: 200, locked: 0)
    OrderStatus.PENDING: BTC(free: 0.01, locked: 0.01) USDT(free: 200, locked: 0) BTC.update_locked(0.01) BTC.update_free(-0.01)
    OrderStatus.PARTIALLY_FILLED: BTC(free: 0.01, locked: 0.005) USDT(free: 350, locked: 0) BTC.update_locked(-0.005) USDT.update_free(150)
    OrderStatus.FILLED: BTC(free: 0.01, locked: 0.0) USDT(free: 500, locked: 0) BTC.update_locked(-0.005) USDT.update_free(150)
    """

    asset: str
    free: Decimal = field(default=Decimal("0.0"))
    locked: Decimal = field(default=Decimal("0.0"))

    @property
    def total(self) -> Decimal:
        return self.free + self.locked


class AccountBalance(Struct):
    balances: Dict[str, Balance] = field(default_factory=dict)

    def _apply(self, balances: List[Balance]):
        for balance in balances:
            self.balances[balance.asset] = balance

    @property
    def balance_total(self) -> Dict[str, Decimal]:
        return {asset: balance.total for asset, balance in self.balances.items()}

    @property
    def balance_free(self) -> Dict[str, Decimal]:
        return {asset: balance.free for asset, balance in self.balances.items()}

    @property
    def balance_locked(self) -> Dict[str, Decimal]:
        return {asset: balance.locked for asset, balance in self.balances.items()}


class Precision(Struct):
    """
     "precision": {
      "amount": 0.0001,
      "price": 1e-05,
      "cost": null,
      "base": 1e-08,
      "quote": 1e-08
    },
    """

    amount: float | None = None
    price: float | None = None
    cost: float | None = None
    base: float | None = None
    quote: float | None = None


class LimitMinMax(Struct):
    """
    "limits": {
      "amount": {
        "min": 0.0001,
        "max": 1000.0
      },
      "price": {
        "min": 1e-05,
        "max": 1000000.0
      },
      "cost": {
        "min": 0.01,
        "max": 1000000.0
      }
    },
    """

    min: float | None
    max: float | None


class Limit(Struct):
    leverage: LimitMinMax = None
    amount: LimitMinMax = None
    price: LimitMinMax = None
    cost: LimitMinMax = None
    market: LimitMinMax = None


class MarginMode(Struct):
    isolated: bool | None
    cross: bool | None


class BaseMarket(Struct):
    """Base market structure for all exchanges."""

    id: str
    lowercaseId: str | None
    symbol: str
    base: str
    quote: str
    settle: str | None
    baseId: str
    quoteId: str
    settleId: str | None
    type: InstrumentType
    spot: bool
    margin: bool | None
    swap: bool
    future: bool
    option: bool
    index: bool | str | None
    active: bool
    contract: bool
    linear: bool | None
    inverse: bool | None
    subType: InstrumentType | None
    taker: float
    maker: float
    contractSize: float | None
    expiry: int | None
    expiryDatetime: str | None
    strike: float | str | None
    optionType: str | None
    precision: Precision
    limits: Limit
    marginModes: MarginMode
    created: int | None
    tierBased: bool | None
    percentage: bool | None
    # feeSide: str  # not supported by okx exchanges


"""
class Position(Struct):

    one-way mode:
    > order (side: buy) -> side: buy | pos_side: net/both | reduce_only: False [open long position]
    > order (side: sell) -> side: sell | pos_side: net/both | reduce_only: False [open short position]
    > order (side: buy, reduce_only=True) -> side: buy | pos_side: net/both | reduce_only: True [close short position]
    > order (side: sell, reduce_only=True) -> side: sell | pos_side: net/both | reduce_only: True [close long position]

    hedge mode:
    > order (side: buy, pos_side: long) -> side: buy | pos_side: long | reduce_only: False [open long position]
    > order (side: sell, pos_side: short) -> side: sell | pos_side: short | reduce_only: False [open short position]
    > order (side: sell, pos_side: long) -> side: sell | pos_side: long | reduce_only: True [close long position]
    > order (side: buy, pos_side: short) -> side: buy | pos_side: short | reduce_only: True [close short position]

    
"""


class Position(Struct):
    symbol: str
    exchange: ExchangeType
    signed_amount: Decimal = Decimal("0")
    entry_price: float = 0
    side: Optional[PositionSide] = None
    unrealized_pnl: float = 0
    realized_pnl: float = 0

    @property
    def amount(self, contract_size: Decimal = Decimal("1")) -> Decimal:
        return abs(self.signed_amount) * contract_size

    @property
    def is_open(self) -> bool:
        return self.amount != 0

    @property
    def is_closed(self) -> bool:
        return not self.is_open

    @property
    def is_long(self) -> bool:
        return self.side == PositionSide.LONG

    @property
    def is_short(self) -> bool:
        return self.side == PositionSide.SHORT


# class SpotPosition(Position):
#     @property
#     def amount(self) -> Decimal:
#         return abs(self.signed_amount)

#     _last_order_filled: Dict[str, Decimal] = field(default_factory=dict)

#     def _calculate_fill_delta(self, order: Order) -> Decimal:
#         """
#         calculate the fill delta of the order, since filled in order is cumulative,
#         we need to calculate the delta of the order
#         """
#         previous_fill = self._last_order_filled.get(order.uuid, Decimal("0"))
#         current_fill = order.filled
#         fill_delta = current_fill - previous_fill
#         if order.status in (OrderStatus.FILLED, OrderStatus.CANCELED):
#             self._last_order_filled.pop(order.uuid, None)
#         else:
#             self._last_order_filled[order.uuid] = order.filled
#         return fill_delta

#     def _apply(self, order: Order):
#         if not order.last_filled:
#             fill_delta = self._calculate_fill_delta(order)
#         else:
#             fill_delta = order.last_filled

#         if order.side == OrderSide.BUY:
#             self.signed_amount += fill_delta
#         elif order.side == OrderSide.SELL:
#             self.signed_amount -= fill_delta


# class Position(Struct):
#     symbol: str
#     exchange: ExchangeType
#     side: Optional[PositionSide] = None
#     signed_amount: Decimal = Decimal("0")
#     entry_price: float = 0
#     unrealized_pnl: float = 0
#     realized_pnl: float = 0
#     _last_order_filled: Dict[str, Decimal] = field(default_factory=dict)

#     @property
#     def amount(self) -> Decimal:
#         return abs(self.signed_amount)

#     @property
#     def is_open(self) -> bool:
#         return self.amount != 0

#     @property
#     def is_closed(self) -> bool:
#         return not self.is_open

#     @property
#     def is_long(self) -> bool:
#         return self.side == PositionSide.LONG

#     @property
#     def is_short(self) -> bool:
#         return self.side == PositionSide.SHORT

#     def _calculate_fill_delta(self, order: Order) -> Decimal:
#         """
#         calculate the fill delta of the order, since filled in order is cumulative,
#         we need to calculate the delta of the order
#         """
#         previous_fill = self._last_order_filled.get(order.uuid, Decimal("0"))
#         current_fill = order.filled
#         fill_delta = current_fill - previous_fill
#         if order.status in (OrderStatus.FILLED, OrderStatus.CANCELED):
#             self._last_order_filled.pop(order.uuid, None)
#         else:
#             self._last_order_filled[order.uuid] = order.filled
#         return fill_delta

#     def _calculate_pnl(self, current_price: float, amount: Decimal) -> float:
#         """Calculate PNL based on position side and current price"""
#         if self.is_long:
#             return float(amount) * (current_price - self.entry_price)
#         elif self.is_short:
#             return float(amount) * (self.entry_price - current_price)
#         return 0.0

#     def apply(self, order: Order):
#         if order.position_side == PositionSide.FLAT:
#             if not order.last_filled:
#                 fill_delta = self._calculate_fill_delta(order)
#             else:
#                 fill_delta = order.last_filled

#             if (self.signed_amount > 0 and order.side == OrderSide.SELL) or (
#                 self.signed_amount < 0 and order.side == OrderSide.BUY
#             ):
#                 close_amount = min(
#                     abs(self.signed_amount), fill_delta
#                 )  # 平仓数量最大不超过当前持仓数量
#                 remaining_amount = fill_delta - close_amount  # 剩余数量
#                 self._close_position(order, close_amount)
#                 if remaining_amount > 0:
#                     self._open_position(order, remaining_amount)
#             else:
#                 self._open_position(order, fill_delta)
#         else:
#             pass

#     def _update_position(
#         self, current_price: float, amount: Decimal, buy_sell: OrderSide
#     ):
#         amount_change = amount if buy_sell == OrderSide.BUY else -amount

#         # 1. update entry price
#         self.entry_price = (
#             (
#                 self.entry_price * float(self.signed_amount)
#                 + current_price * float(amount_change)
#             )
#             / float(self.signed_amount + amount_change)
#             if self.signed_amount + amount_change != 0
#             else 0
#         )

#         # 2. update signed amount
#         self.signed_amount += amount_change

#         # 3. update unrealized pnl
#         self.unrealized_pnl = self._calculate_pnl(current_price, self.amount)

#     def _close_position(self, order: Order, close_amount: Decimal):
#         if order.side == OrderSide.BUY:
#             if not self.is_short:
#                 warnings.warn(f"Cannot close short position with {self.side}")
#         elif order.side == OrderSide.SELL:
#             if not self.is_long:
#                 warnings.warn(f"Cannot close long position with {self.side}")

#         price = order.average or order.price
#         self._update_position(price, close_amount, order.side)
#         self.realized_pnl += self._calculate_pnl(price, close_amount)

#         if self.signed_amount == 0:
#             self.side = None
#             self.entry_price = 0
#             self.unrealized_pnl = 0

#     def _open_position(self, order: Order, open_amount: Decimal):
#         if order.side == OrderSide.BUY:
#             if not self.side:
#                 self.side = PositionSide.LONG
#             else:
#                 if not self.is_long:
#                     warnings.warn(f"Cannot open long position with {self.side}")

#         elif order.side == OrderSide.SELL:
#             if not self.side:
#                 self.side = PositionSide.SHORT
#             else:
#                 if not self.is_short:
#                     warnings.warn(f"Cannot open short position with {self.side}")

#         price = order.average or order.price
#         self._update_position(price, open_amount, order.side)
