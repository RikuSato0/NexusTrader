

cdef class BookL1:
    def __init__(self, str exchange, str symbol, double bid, double ask, double bid_size, double ask_size, long timestamp):
        self.exchange = exchange
        self.symbol = symbol
        self.bid = bid
        self.ask = ask
        self.bid_size = bid_size
        self.ask_size = ask_size
        self.timestamp = timestamp
    
    def __repr__(self) -> str:
        return f"BookL1(exchange={self.exchange}, symbol={self.symbol}, bid={self.bid}, ask={self.ask}, bid_size={self.bid_size}, ask_size={self.ask_size}) timestamp={self.timestamp}"
    
    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, BookL1):
            return False
        return self.exchange == __o.exchange and self.symbol == __o.symbol and self.bid == __o.bid and self.ask == __o.ask and self.bid_size == __o.bid_size and self.ask_size == __o.ask_size

cdef class Trade:
    def __init__(self, str exchange, str symbol, double price, double size, long timestamp):
        self.exchange = exchange
        self.symbol = symbol
        self.price = price
        self.size = size
        self.timestamp = timestamp

    def __repr__(self) -> str:
        return f"Trade(exchange={self.exchange}, symbol={self.symbol}, price={self.price}, size={self.size}, timestamp={self.timestamp})"

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Trade):
            return False
        return (
            self.exchange == __o.exchange and
            self.symbol == __o.symbol and
            self.price == __o.price and
            self.size == __o.size and
            self.timestamp == __o.timestamp
        )

cdef class Kline:

    def __init__(self, str exchange, str symbol, str interval, double open, double high, double low, double close, double volume, long timestamp):
        self.exchange = exchange
        self.symbol = symbol
        self.interval = interval
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.timestamp = timestamp

    def __repr__(self) -> str:
        return (f"Kline(exchange={self.exchange}, symbol={self.symbol}, interval={self.interval}, "
                f"open={self.open}, high={self.high}, low={self.low}, close={self.close}, "
                f"volume={self.volume}, timestamp={self.timestamp})")

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Kline):
            return False
        return (
            self.exchange == __o.exchange and
            self.symbol == __o.symbol and
            self.interval == __o.interval and
            self.open == __o.open and
            self.high == __o.high and
            self.low == __o.low and
            self.close == __o.close and
            self.volume == __o.volume and
            self.timestamp == __o.timestamp
        )

cdef class MarkPrice:

    def __init__(self, str exchange, str symbol, double price, long timestamp):
        self.exchange = exchange
        self.symbol = symbol
        self.price = price
        self.timestamp = timestamp

    def __repr__(self) -> str:
        return f"MarkPrice(exchange={self.exchange}, symbol={self.symbol}, price={self.price}, timestamp={self.timestamp})"

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, MarkPrice):
            return False
        return (
            self.exchange == __o.exchange and
            self.symbol == __o.symbol and
            self.price == __o.price and
            self.timestamp == __o.timestamp
        )

cdef class FundingRate:

    def __init__(self, str exchange, str symbol, double rate, long timestamp, long next_funding_time):
        self.exchange = exchange
        self.symbol = symbol
        self.rate = rate
        self.timestamp = timestamp
        self.next_funding_time = next_funding_time

    def __repr__(self) -> str:
        return (f"FundingRate(exchange={self.exchange}, symbol={self.symbol}, rate={self.rate}, "
                f"timestamp={self.timestamp}, next_funding_time={self.next_funding_time})")

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, FundingRate):
            return False
        return (
            self.exchange == __o.exchange and
            self.symbol == __o.symbol and
            self.rate == __o.rate and
            self.timestamp == __o.timestamp and
            self.next_funding_time == __o.next_funding_time
        )

cdef class IndexPrice:

    def __init__(self, str exchange, str symbol, double price, long timestamp):
        self.exchange = exchange
        self.symbol = symbol
        self.price = price
        self.timestamp = timestamp

    def __repr__(self) -> str:
        return f"IndexPrice(exchange={self.exchange}, symbol={self.symbol}, price={self.price}, timestamp={self.timestamp})"

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, IndexPrice):
            return False
        return (
            self.exchange == __o.exchange and
            self.symbol == __o.symbol and
            self.price == __o.price and
            self.timestamp == __o.timestamp
        )
