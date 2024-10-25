cdef class BookL1:
    cdef readonly str exchange
    cdef readonly str symbol
    cdef readonly double bid
    cdef readonly double ask
    cdef readonly double bid_size
    cdef readonly double ask_size
    cdef readonly long timestamp

cdef class Trade:
    cdef readonly str exchange
    cdef readonly str symbol
    cdef readonly double price
    cdef readonly double size
    cdef readonly long timestamp

cdef class Kline:
    cdef readonly str exchange
    cdef readonly str symbol
    cdef readonly str interval
    cdef readonly double open
    cdef readonly double high
    cdef readonly double low
    cdef readonly double close
    cdef readonly double volume
    cdef readonly long timestamp

cdef class MarkPrice:
    cdef readonly str exchange
    cdef readonly str symbol
    cdef readonly double price
    cdef readonly long timestamp

cdef class FundingRate:
    cdef readonly str exchange
    cdef readonly str symbol
    cdef readonly double rate
    cdef readonly long timestamp
    cdef readonly long next_funding_time

cdef class IndexPrice:
    cdef readonly str exchange
    cdef readonly str symbol
    cdef readonly double price
    cdef readonly long timestamp

# cdef class Order:
#     cdef readonly object raw
#     cdef readonly bool success
#     cdef readonly str exchange
#     cdef readonly str id
#     cdef readonly str client_order_id
#     cdef readonly long timestamp
#     cdef readonly str symbol
#     cdef readonly str type
#     cdef readonly str side
#     cdef readonly str status
#     cdef readonly double price
#     cdef readonly double average
#     cdef readonly double last_filled_price
#     cdef readonly object amount
#     cdef readonly object filled
#     cdef readonly object last_filled
#     cdef readonly object remaining
#     cdef readonly double fee
#     cdef readonly str fee_currency
#     cdef readonly double cost
#     cdef readonly long last_trade_timestamp
#     cdef readonly bool reduce_only
#     cdef readonly str position_side
#     cdef readonly str time_in_force
#     cdef readonly int leverage
