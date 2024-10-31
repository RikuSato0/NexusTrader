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
        self.free -= amount
    
    def _set_value(self, free: Decimal, borrowed: Decimal, locked: Decimal):
        if free is not None:
            self.free = free
        if borrowed is not None:
            self.borrowed = borrowed 
        if locked is not None:
            self.locked = locked



    