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
    






