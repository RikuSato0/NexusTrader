import json
import time
from statistics import mean, stdev
import orjson
import msgspec
from tradebot.types import BookL1, Trade, Kline
from typing import Any, Dict



class BncEventMsg(msgspec.Struct):
    e: str
    
    @property
    def is_event(self):
        return True

class BncTradeMsg(msgspec.Struct):
    s: str
    p: str
    q: str
    T: int
    
    def parse_to_trade(self):
        return Trade(
            exchange="binance",
            symbol=self.s,
            price=float(self.p),
            size=float(self.q),
            timestamp=self.T,
        )

class BncBookTickerMsg(msgspec.Struct):
    s: str
    b: str
    a: str
    B: str
    A: str
    T: int
    
    def parse_to_book_ticker(self):
        return BookL1(
            exchange="binance",
            symbol=self.s,
            bid=float(self.b),
            ask=float(self.a),
            bid_size=float(self.B),
            ask_size=float(self.A),
            timestamp=self.T,
        )

class BncKlineMsg(msgspec.Struct):
    s: str
    k: Dict[str, Any]
    E: int
    
    def parse_to_kline(self):
        return Kline(
            exchange="binance",
            symbol=self.s,
            interval=self.k["i"],
            open=float(self.k["o"]),
            high=float(self.k["h"]),
            low=float(self.k["l"]),
            close=float(self.k["c"]),
            volume=float(self.k["v"]),
            timestamp=self.E,
        )



def msg_ws_handler(msg, event_decoder, trade_decoder, book_ticker_decoder, kline_decoder):
    try:
        event = event_decoder.decode(msg, type=BncEventMsg)
    except:
        return
    
    if event.is_event:
        if event.e == "trade":
            trade = trade_decoder.decode(msg, type=BncTradeMsg)
            trade = trade.parse_to_trade()
        elif event.e == "bookTicker":
            book_ticker = book_ticker_decoder.decode(msg, type=BncBookTickerMsg)
            book_ticker = book_ticker.parse_to_book_ticker()
        elif event.e == "kline":
            kline = kline_decoder.decode(msg, type=BncKlineMsg)
            kline = kline.parse_to_kline()



def ws_msg_handler(msg):
    if "e" in msg:
        match msg["e"]:
            case "trade":
                parse_trade(msg)
            case "bookTicker":
                parse_book_ticker(msg)
            case "kline":
                parse_kline(msg)
    elif "u" in msg:
        # spot book ticker doesn't have "e" key. FUCK BINANCE
        parse_book_ticker(msg)
        
def parse_kline(res: Dict[str, Any]) -> Kline:
    """
    {
        "e": "kline",     // Event type
        "E": 1672515782136,   // Event time
        "s": "BNBBTC",    // Symbol
        "k": {
            "t": 123400000, // Kline start time
            "T": 123460000, // Kline close time
            "s": "BNBBTC",  // Symbol
            "i": "1m",      // Interval
            "f": 100,       // First trade ID
            "L": 200,       // Last trade ID
            "o": "0.0010",  // Open price
            "c": "0.0020",  // Close price
            "h": "0.0025",  // High price
            "l": "0.0015",  // Low price
            "v": "1000",    // Base asset volume
            "n": 100,       // Number of trades
            "x": false,     // Is this kline closed?
            "q": "1.0000",  // Quote asset volume
            "V": "500",     // Taker buy base asset volume
            "Q": "0.500",   // Taker buy quote asset volume
            "B": "123456"   // Ignore
        }
    }
    """
    ticker = Kline(
        exchange="binance",
        symbol=res["s"],
        interval=res["k"]["i"],
        open=float(res["k"]["o"]),
        high=float(res["k"]["h"]),
        low=float(res["k"]["l"]),
        close=float(res["k"]["c"]),
        volume=float(res["k"]["v"]),
        timestamp=res.get("E", time.time_ns() // 1_000_000),
    )
    return ticker
    
    
def parse_trade(res: Dict[str, Any]) -> Trade:
    """
    {
        "e": "trade",       // Event type
        "E": 1672515782136, // Event time
        "s": "BNBBTC",      // Symbol
        "t": 12345,         // Trade ID
        "p": "0.001",       // Price
        "q": "100",         // Quantity
        "T": 1672515782136, // Trade time
        "m": true,          // Is the buyer the market maker?
        "M": true           // Ignore
    }
    {
        "u":400900217,     // order book updateId
        "s":"BNBUSDT",     // symbol
        "b":"25.35190000", // best bid price
        "B":"31.21000000", // best bid qty
        "a":"25.36520000", // best ask price
        "A":"40.66000000"  // best ask qty
    }
    """
    trade = Trade(
        exchange="binance",
        symbol=res["s"],
        price=float(res["p"]),
        size=float(res["q"]),
        timestamp=res.get("T", time.time_ns() // 1_000_000),
    )
    return trade
    
    
def parse_book_ticker(res: Dict[str, Any]) -> BookL1:
    """
    {
        "u":400900217,     // order book updateId
        "s":"BNBUSDT",     // symbol
        "b":"25.35190000", // best bid price
        "B":"31.21000000", // best bid qty
        "a":"25.36520000", // best ask price
        "A":"40.66000000"  // best ask qty
    }
    """
    bookl1 = BookL1(
        exchange="binance",
        symbol=res["s"],
        bid=float(res["b"]),
        ask=float(res["a"]),
        bid_size=float(res["B"]),
        ask_size=float(res["A"]),
        timestamp=res.get("T", time.time_ns() // 1_000_000),
    )
    return bookl1
    



def generate_test_data():
    with open("benchmark/test_data/data.json", "rb") as f:
        data = orjson.loads(f.read())

    return data

def orjson_decoder(data):
    return orjson.loads(data)

def msgspec_decoder(data, decoder):
    return decoder.decode(data)

def test_orjson(data):
    for event in data:
        msg = orjson_decoder(event)
        ws_msg_handler(msg)
    

def test_msgspec(data):
    event_decoder = msgspec.json.Decoder(BncEventMsg)
    trade_decoder = msgspec.json.Decoder(BncTradeMsg)
    book_ticker_decoder = msgspec.json.Decoder(BncBookTickerMsg)
    kline_decoder = msgspec.json.Decoder(BncKlineMsg)
    
    
    
    for event in data:
        # msg = msgspec_decoder(event, decoder)
        msg_ws_handler(event, event_decoder, trade_decoder, book_ticker_decoder, kline_decoder)


def run_benchmark(n_iterations):
    test_data = generate_test_data()

    # JIT Warm-up ?
    # 在正式计时前运行一些迭代，以确保 JIT 优化已经应用
    # for _ in range(1000):
    #     test_orjson(test_data[:10])
    #     test_msgspec(test_data[:10], msgspec_decoder)

    orjson_times = []
    msgspec_times = []

    for _ in range(n_iterations):
        start = time.perf_counter()
        test_orjson(test_data)
        orjson_times.append(time.perf_counter() - start)

        start = time.perf_counter()
        test_msgspec(test_data)
        msgspec_times.append(time.perf_counter() - start)

    print(f"orjson:  {mean(orjson_times):.6f} ± {stdev(orjson_times):.6f} seconds")
    print(f"msgspec: {mean(msgspec_times):.6f} ± {stdev(msgspec_times):.6f} seconds")


def test1():
    dict_ = json.dumps(
        {
            "id": 1,
            "name": f"User{1}",
            "email": f"user{1}@example.com",
            "age": 20 + (1 % 50),
            "is_active": 1 % 2 == 0,
            "score": round(1 / 10, 2),
        }
    )
    msgspec_decoder = msgspec.json.Decoder()

    data = msgspec_decoder.decode(dict_)
    print(type(data))
    print(data)
    print(data.age)


if __name__ == "__main__":
    N_ITERATIONS = 20

    print(
        f"Benchmarking with {N_ITERATIONS} iterations:"
    )
    run_benchmark(N_ITERATIONS)
