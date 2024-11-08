import msgspec
from typing import Final


BYBIT_PONG: Final[str] = "pong"

class BybitWsMessageGeneral(msgspec.Struct):
    op: str | None = None
    topic: str | None = None
    success: bool | None = None
    ret_msg: str | None = None

class BybitWsOrderbookDepth(msgspec.Struct):
    # symbol
    s: str
    # bids
    b: list[list[str]]
    # asks
    a: list[list[str]]
    # Update ID. Is a sequence. Occasionally, you'll receive "u"=1, which is a
    # snapshot data due to the restart of the service.
    u: int
    # Cross sequence
    seq: int

class BybitWsOrderbookDepthMsg(msgspec.Struct):
    topic: str
    type: str
    ts: int
    data: BybitWsOrderbookDepth
