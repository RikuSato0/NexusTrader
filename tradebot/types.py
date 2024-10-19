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




