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
