from decimal import Decimal
from collections import defaultdict
from typing import Any, Dict, List, Tuple
from typing import Literal, Optional
from msgspec import Struct, field
from tradebot.constants import OrderSide, OrderType, TimeInForce, OrderStatus, PositionSide, AssetType


class BookL1(Struct, gc=False):
    exchange: str
    symbol: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    timestamp: int

class BookL2(Struct):
    exchange: str
    symbol: str
    bids: List[Tuple[float, float]]
    asks: List[Tuple[float, float]]
    timestamp: int


class Trade(Struct, gc=False):
    exchange: str
    symbol: str
    price: float
    size: float
    timestamp: int


class Kline(Struct, gc=False):
    exchange: str
    symbol: str
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: int


class MarkPrice(Struct, gc=False):
    exchange: str
    symbol: str
    price: float
    timestamp: int


class FundingRate(Struct, gc=False):
    exchange: str
    symbol: str
    rate: float
    timestamp: int
    next_funding_time: int


class IndexPrice(Struct, gc=False):
    exchange: str
    symbol: str
    price: float
    timestamp: int

class Order(Struct):
    exchange: str
    symbol: str
    status: OrderStatus 
    id: str = None
    client_order_id: str = None
    timestamp: int = None
    type: OrderType = None
    side: OrderSide = None
    time_in_force: Optional[TimeInForce] = None
    price: Optional[float] = None
    average: Optional[float] = None
    last_filled_price: Optional[float] = None
    amount: Optional[Decimal] = None
    filled: Optional[Decimal] = None
    last_filled: Optional[Decimal] = None
    remaining: Optional[Decimal] = None
    fee: Optional[float] = None
    fee_currency: Optional[str] = None
    cost: Optional[float] = None
    cum_cost: Optional[float] = None
    reduce_only: Optional[bool] = None
    position_side: Optional[PositionSide] = None
    
    @property
    def success(self) -> bool:
        return self.status != OrderStatus.FAILED

class Asset(Struct):
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
    borrowed: Decimal = field(default=Decimal("0.0"))
    locked: Decimal = field(default=Decimal("0.0"))

    @property
    def total(self) -> Decimal:
        return self.free + self.locked

    def _update_free(self, amount: Decimal):
        """
        if amount > 0, then it is a buying action
        if amount < 0, then it is a selling action
        """
        self.free += amount

    def _update_borrowed(self, amount: Decimal):
        """
        if amount > 0, then it is a borrowing action
        if amount < 0, then it is a repayment action
        """
        self.borrowed += amount
        self.free += amount

    def _update_locked(self, amount: Decimal):
        """
        if amount > 0, then it is a new order action
        if amount < 0, then it is a cancellation/filled/partially filled action
        """
        self.locked += amount
    
    def _set_value(self, free: Decimal, borrowed: Decimal, locked: Decimal):
        if free is not None:
            self.free = free
        if borrowed is not None:
            self.borrowed = borrowed 
        if locked is not None:
            self.locked = locked


class Position(Struct):
    """
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
    symbol: str
    exchange: str
    pos_side: Literal["long", "short"]
    amount: Decimal # order amount, the unit could be base amount or contract amount
    size: Decimal # must be the determined unit
    avg_open_price: Decimal
    avg_close_price: Decimal


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
    type: AssetType
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
    subType: AssetType | None
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
    tierBased: bool
    percentage: bool
    feeSide: str

class MarketData(Struct):
    bookl1: Dict[str, Dict[str, BookL1]] = defaultdict(dict)
    bookl2: Dict[str, Dict[str, BookL2]] = defaultdict(dict)
    trade: Dict[str, Dict[str, Trade]] = defaultdict(dict)
    kline: Dict[str, Dict[str, Kline]] = defaultdict(dict)
    mark_price: Dict[str, Dict[str, MarkPrice]] = defaultdict(dict)
    funding_rate: Dict[str, Dict[str, FundingRate]] = defaultdict(dict)
    index_price: Dict[str, Dict[str, IndexPrice]] = defaultdict(dict)
    
    def update_bookl1(self, bookl1: BookL1):
        self.bookl1[bookl1.exchange][bookl1.symbol] = bookl1
    
    def update_bookl2(self, bookl2: BookL2):
        self.bookl2[bookl2.exchange][bookl2.symbol] = bookl2
    
    def update_trade(self, trade: Trade):
        self.trade[trade.exchange][trade.symbol] = trade
    
    def update_kline(self, kline: Kline):
        self.kline[kline.exchange][kline.symbol] = kline
    
    def update_mark_price(self, mark_price: MarkPrice):
        self.mark_price[mark_price.exchange][mark_price.symbol] = mark_price
    
    def update_funding_rate(self, funding_rate: FundingRate):
        self.funding_rate[funding_rate.exchange][funding_rate.symbol] = funding_rate
    
    def update_index_price(self, index_price: IndexPrice):
        self.index_price[index_price.exchange][index_price.symbol] = index_price
    
    