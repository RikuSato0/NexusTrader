import orjson
import msgspec
from enum import Enum

class BinanceExecutionType(Enum):
    NEW = "NEW"
    CANCELED = "CANCELED"
    CALCULATED = "CALCULATED"  
    REJECTED = "REJECTED"
    TRADE = "TRADE"
    EXPIRED = "EXPIRED"
    AMENDMENT = "AMENDMENT"
    TRADE_PREVENTION = "TRADE_PREVENTION"

class BinanceOrderStatus(Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    PENDING_CANCEL = "PENDING_CANCEL"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    EXPIRED_IN_MATCH = "EXPIRED_IN_MATCH"
    NEW_INSURANCE = "NEW_INSURANCE"  
    NEW_ADL = "NEW_ADL"  
    

class BinanceFuturesOrderData(msgspec.Struct):
    s: str
    c: str
    S: str
    o: str
    f: str
    q: str
    p: str
    ap: str
    sp: str
    x: BinanceExecutionType
    X: BinanceOrderStatus
    i: int
    l: str
    z: str
    L: str
    n: str
    N: str
    T: int
    t: int
    b: str
    a: str
    m: bool
    R: bool
    ps: str
    rp: str
    V: str
    pm: str
    gtd: int


class BinanceFuturesOrderUpdateMsg(msgspec.Struct):
    e: str
    T: int
    E: int
    fs: str = None
    o: BinanceFuturesOrderData = None

    




raw = b'{"e": "ORDER_TRADE_UPDATE", "T": 1727353874116, "E": 1727353874124, "fs": "UM", "o": {"s": "AVAXUSDT", "c": "c-11WLU7VP2rj4ss0i", "S": "SELL", "o": "LIMIT", "f": "GTC", "q": "3", "p": "28.4960", "ap": "28.4960", "sp": "0", "x": "TRADE", "X": "FILLED", "i": 23560120539, "l": "3", "z": "3", "L": "28.4960", "n": "0", "N": "USDT", "T": 1727353874116, "t": 879287954, "b": "0", "a": "0", "m": true, "R": false, "ps": "BOTH", "rp": "0", "V": "EXPIRE_NONE", "pm": "PM_NONE", "gtd": 0}}'

data = orjson.loads(raw)


data:BinanceFuturesOrderUpdateMsg = msgspec.json.decode(raw, type=BinanceFuturesOrderUpdateMsg)

print(data)
assert data.o.X == BinanceOrderStatus.FILLED
