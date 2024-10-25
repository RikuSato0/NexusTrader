from decimal import Decimal
from dataclasses import dataclass, field
from typing import Any, Dict
from typing import Literal, Optional
from msgspec import Struct


# @dataclass(slots=True)
# class BookL1:
#     exchange: str
#     symbol: str
#     bid: float
#     ask: float
#     bid_size: float
#     ask_size: float
#     timestamp: int


class BookL1(Struct, gc=False):
    exchange: str
    symbol: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    timestamp: int


# @dataclass(slots=True)
# class Trade:
#     exchange: str
#     symbol: str
#     price: float
#     size: float
#     timestamp: int


class Trade(Struct, gc=False):
    exchange: str
    symbol: str
    price: float
    size: float
    timestamp: int


# @dataclass(slots=True)
# class Kline:
#     exchange: str
#     symbol: str
#     interval: str
#     open: float
#     high: float
#     low: float
#     close: float
#     volume: float
#     timestamp: int


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


# @dataclass(slots=True)
# class MarkPrice:
#     exchange: str
#     symbol: str
#     price: float
#     timestamp: int


class MarkPrice(Struct, gc=False):
    exchange: str
    symbol: str
    price: float
    timestamp: int


# @dataclass(slots=True)
# class FundingRate:
#     exchange: str
#     symbol: str
#     rate: float
#     timestamp: int
#     next_funding_time: int


class FundingRate(Struct, gc=False):
    exchange: str
    symbol: str
    rate: float
    timestamp: int
    next_funding_time: int


# @dataclass(slots=True)
# class IndexPrice:
#     exchange: str
#     symbol: str
#     price: float
#     timestamp: int


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


# @dataclass
# class Order:
#     raw: Dict[str, Any]
#     success: bool
#     exchange: str
#     id: str
#     client_order_id: str
#     timestamp: int
#     symbol: str
#     type: Literal["limit", "market"]
#     side: Literal["buy", "sell"]
#     status: Literal[
#         "new", "partially_filled", "filled", "canceled", "expired", "failed"
#     ]
#     price: Optional[float] = None
#     average: Optional[float] = None
#     last_filled_price: Optional[float] = None
#     amount: Optional[Decimal] = None
#     filled: Optional[Decimal] = None
#     last_filled: Optional[Decimal] = None
#     remaining: Optional[Decimal] = None
#     fee: Optional[float] = None
#     fee_currency: Optional[str] = None
#     cost: Optional[float] = None
#     last_trade_timestamp: Optional[int] = None
#     reduce_only: Optional[bool] = None
#     position_side: Optional[str] = None
#     time_in_force: Optional[str] = None
#     leverage: Optional[int] = None

#     def __post_init__(self):
#         decimal_fields = ["amount", "filled", "last_filled", "remaining"]

#         for decimal_field in decimal_fields:
#             if getattr(self, decimal_field) is not None and not isinstance(
#                 getattr(self, decimal_field), Decimal
#             ):
#                 setattr(self, decimal_field, Decimal(str(getattr(self, decimal_field))))

#         float_fields = ["price", "average", "last_filled_price", "fee", "cost"]
#         for float_field in float_fields:
#             if getattr(self, float_field) is not None and not isinstance(
#                 getattr(self, float_field), float
#             ):
#                 setattr(self, float_field, float(getattr(self, float_field)))
