from decimal import Decimal
from typing import Any, Dict
from typing import Literal, Optional
from msgspec import Struct, field


class BookL1(Struct, gc=False):
    exchange: str
    symbol: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
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
    raw: Dict[str, Any]
    success: bool
    exchange: str
    id: str
    client_order_id: str
    timestamp: int
    symbol: str
    type: Literal["limit", "market"]
    side: Literal["buy", "sell"]
    status: Literal[
        "new", "partially_filled", "filled", "canceled", "expired", "failed"
    ]
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
    last_trade_timestamp: Optional[int] = None
    reduce_only: Optional[bool] = None
    position_side: Optional[str] = None
    time_in_force: Optional[str] = None
    leverage: Optional[int] = None


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
    


    