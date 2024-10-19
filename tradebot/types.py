from dataclasses import dataclass


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



