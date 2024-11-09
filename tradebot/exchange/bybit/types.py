import msgspec
from typing import Final
from typing import Dict, Any


BYBIT_PONG: Final[str] = "pong"

class BybitOrderResult(msgspec.Struct):
    orderId: str
    orderLinkId: str

class BybitOrderResponse(msgspec.Struct):
    retCode: int
    retMsg: str
    result: BybitOrderResult
    time: int

class BybitResponse(msgspec.Struct, frozen=True):
    retCode: int
    retMsg: str
    result: Dict[str, Any]
    time: int
    retExtInfo: Dict[str, Any] | None = None

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

class BybitOrderBook(msgspec.Struct):
    bids: Dict[float, float] = {}
    asks: Dict[float, float] = {}

    def parse_orderbook_depth(self, msg: BybitWsOrderbookDepthMsg, levels: int = 1):
        if msg.type == "snapshot":
            self._handle_snapshot(msg.data)
        elif msg.type == "delta":
            self._handle_delta(msg.data)
        return self._get_orderbook(levels)

    def _handle_snapshot(self, data: BybitWsOrderbookDepth) -> None:
        self.bids.clear()
        self.asks.clear()

        for price, size in data.b:
            self.bids[float(price)] = float(size)

        for price, size in data.a:
            self.asks[float(price)] = float(size)

    def _handle_delta(self, data: BybitWsOrderbookDepth) -> None:
        for price, size in data.b:
            if float(size) == 0:
                self.bids.pop(float(price))
            else:
                self.bids[float(price)] = float(size)

        for price, size in data.a:
            if float(size) == 0:
                self.asks.pop(float(price))
            else:
                self.asks[float(price)] = float(size)

    def _get_orderbook(self, levels: int):
        bids = sorted(self.bids.items(), reverse=True)[:levels]  # bids descending
        asks = sorted(self.asks.items())[:levels]  # asks ascending
        return {
            "bids": bids,
            "asks": asks,
        }
