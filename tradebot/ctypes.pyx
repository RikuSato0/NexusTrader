cimport cython

@cython.freelist(128)
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

@cython.freelist(128)
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


# @cython.freelist(128)
# cdef class Order:
#     def __init__(self, object raw, bool success, str exchange, str id, str client_order_id, long timestamp,
#                  str symbol, str type, str side, str status, double price = None, double average= None,
#                  double last_filled_price= None, object amount= None, object filled= None, object last_filled= None,
#                  object remaining= None, double fee= None, str fee_currency= None, double cost= None, long last_trade_timestamp= None,
#                  bool reduce_only= None, str position_side= None, str time_in_force= None, int leverage= None):
#         self.raw = raw
#         self.success = success
#         self.exchange = exchange
#         self.id = id
#         self.client_order_id = client_order_id
#         self.timestamp = timestamp
#         self.symbol = symbol
#         self.type = type
#         self.side = side
#         self.status = status
#         self.price = price
#         self.average = average
#         self.last_filled_price = last_filled_price
#         self.amount = amount
#         self.filled = filled
#         self.last_filled = last_filled
#         self.remaining = remaining
#         self.fee = fee
#         self.fee_currency = fee_currency
#         self.cost = cost
#         self.last_trade_timestamp = last_trade_timestamp
#         self.reduce_only = reduce_only
#         self.position_side = position_side
#         self.time_in_force = time_in_force
#         self.leverage = leverage

#     def __repr__(self) -> str:
#         return "Order(exchange={}, id={}, client_order_id={}, timestamp={}, symbol={}, type={}, side={}, status={}, price={}, average={}, last_filled_price={}, amount={}, filled={}, last_filled={}, remaining={}, fee={}, fee_currency={}, cost={}, last_trade_timestamp={}, reduce_only={}, position_side={}, time_in_force={}, leverage={})".format(
#             self.exchange, self.id, self.client_order_id, self.timestamp, self.symbol, self.type, self.side, self.status, self.price, self.average, self.last_filled_price, self.amount, self.filled, self.last_filled, self.remaining, self.fee, self.fee_currency, self.cost, self.last_trade_timestamp, self.reduce_only, self.position_side, self.time_in_force, self.leverage
#         )
        

#     def __eq__(self, __o: object) -> bool:
#         if not isinstance(__o, Order):
#             return False
#         return (
#             self.raw == __o.raw and
#             self.success == __o.success and
#             self.exchange == __o.exchange and
#             self.id == __o.id and
#             self.client_order_id == __o.client_order_id and
#             self.timestamp == __o.timestamp and
#             self.symbol == __o.symbol and
#             self.type == __o.type and
#             self.side == __o.side and
#             self.status == __o.status and
#             self.price == __o.price and
#             self.average == __o.average and
#             self.last_filled_price == __o.last_filled_price and
#             self.amount == __o.amount and
#             self.filled == __o.filled and
#             self.last_filled == __o.last_filled and
#             self.remaining == __o.remaining and
#             self.fee == __o.fee and
#             self.fee_currency == __o.fee_currency and
#             self.cost == __o.cost and
#             self.last_trade_timestamp == __o.last_trade_timestamp and
#             self.reduce_only == __o.reduce_only and
#             self.position_side == __o.position_side and
#             self.time_in_force == __o.time_in_force and
#             self.leverage == __o.leverage
#         )
        