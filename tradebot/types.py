from decimal import Decimal
from dataclasses import dataclass, field
from typing import Any, Dict
from typing import Literal, Optional


@dataclass(slots=True)
class BookL1:
    exchange: str
    symbol: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    timestamp: int

@dataclass(slots=True)
class Trade:
    exchange: str
    symbol: str
    price: float
    size: float
    timestamp: int
    

@dataclass(slots=True)
class Kline:
    exchange: str
    symbol: str
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: int

@dataclass(slots=True)
class MarkPrice:
    exchange: str
    symbol: str
    price: float
    timestamp: int

@dataclass(slots=True)
class FundingRate:
    exchange: str
    symbol: str
    rate: float
    timestamp: int
    next_funding_time: int

@dataclass(slots=True)
class IndexPrice:
    exchange: str
    symbol: str
    price: float
    timestamp: int


@dataclass
class Order:
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
    price: Optional[float] = field(default=None)
    average: Optional[float] = field(default=None)
    last_filled_price: Optional[float] = field(default=None)
    amount: Optional[Decimal] = field(default=None)
    filled: Optional[Decimal] = field(default=None)
    last_filled: Optional[Decimal] = field(default=None)
    remaining: Optional[Decimal] = field(default=None)
    fee: Optional[float] = field(default=None)
    fee_currency: Optional[str] = field(default=None)
    cost: Optional[float] = field(default=None)
    last_trade_timestamp: Optional[int] = field(default=None)
    reduce_only: Optional[bool] = field(default=None)
    position_side: Optional[str] = field(default=None)
    time_in_force: Optional[str] = field(default=None)
    leverage: Optional[int] = field(default=None)

    def __post_init__(self):
        decimal_fields = ["amount", "filled", "last_filled", "remaining"]

        for field in decimal_fields:
            if getattr(self, field) is not None and not isinstance(
                getattr(self, field), Decimal
            ):
                setattr(self, field, Decimal(str(getattr(self, field))))

        float_fields = ["price", "average", "last_filled_price", "fee", "cost"]
        for field in float_fields:
            if getattr(self, field) is not None and not isinstance(
                getattr(self, field), float
            ):
                setattr(self, field, float(getattr(self, field)))
