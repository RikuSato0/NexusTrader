import time

from typing import Dict, Any

from tradebot.base import PublicConnector
from tradebot.entity import EventSystem
from tradebot.constants import EventType
from tradebot.ctypes import BookL1, Trade, Kline, MarkPrice, FundingRate, IndexPrice

from tradebot.exchange.binance.constants import BinanceAccountType
from tradebot.exchange.binance.websockets import BinanceWSClient


class BinancePublicConnector(PublicConnector):
    def __init__(
        self,
        accout_type: BinanceAccountType,
        market: Dict[str, Any],
        market_id: Dict[str, Any],
    ):
        super().__init__(
            account_type=accout_type,
            market=market,
            market_id=market_id,
            exchange_id="binance",
        )

        self._ws_client = BinanceWSClient(
            account_type=accout_type, handler=self._ws_msg_handler
        )

    @property
    def market_type(self):
        if self._account_type.is_spot:
            return "_spot"
        elif self._account_type.is_linear:
            return "_linear"
        elif self._account_type.is_inverse:
            return "_inverse"

    async def subscribe_trade(self, symbol: str):
        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol
        await self._ws_client.subscribe_trade(symbol)

    async def subscribe_bookl1(self, symbol: str):
        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol
        await self._ws_client.subscribe_book_ticker(symbol)
    
    async def subscribe_kline(self, symbol: str, interval: str):
        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol
        await self._ws_client.subscribe_kline(symbol, interval)
    
    def _ws_msg_handler(self, msg):
        if "e" in msg:
            match msg["e"]:
                case "trade":
                    self._parse_trade(msg)
                case "bookTicker":
                    self._parse_book_ticker(msg)
                case "kline":
                    self._parse_kline(msg)
                case "markPriceUpdate":
                    self._parse_mark_price(msg)
        elif "u" in msg:
            # spot book ticker doesn't have "e" key. FUCK BINANCE
            self._parse_book_ticker(msg)

    def _parse_kline(self, res: Dict[str, Any]) -> Kline:
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
        id = res["s"] + self.market_type
        market = self._market_id[id]

        ticker = Kline(
            exchange=self._exchange_id,
            symbol=market["symbol"],
            interval=res["k"]["i"],
            open=float(res["k"]["o"]),
            high=float(res["k"]["h"]),
            low=float(res["k"]["l"]),
            close=float(res["k"]["c"]),
            volume=float(res["k"]["v"]),
            timestamp=res.get("E", time.time_ns() // 1_000_000),
        )
        EventSystem.emit(EventType.KLINE, ticker)

    def _parse_trade(self, res: Dict[str, Any]) -> Trade:
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
        id = res["s"] + self.market_type
        market = self._market_id[id]  # map exchange id to ccxt symbol

        trade = Trade(
            exchange=self._exchange_id,
            symbol=market["symbol"],
            price=float(res["p"]),
            size=float(res["q"]),
            timestamp=res.get("T", time.time_ns() // 1_000_000),
        )
        EventSystem.emit(EventType.TRADE, trade)

    def _parse_book_ticker(self, res: Dict[str, Any]) -> BookL1:
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
        id = res["s"] + self.market_type
        market = self._market_id[id]

        bookl1 = BookL1(
            exchange=self._exchange_id,
            symbol=market["symbol"],
            bid=float(res["b"]),
            ask=float(res["a"]),
            bid_size=float(res["B"]),
            ask_size=float(res["A"]),
            timestamp=res.get("T", time.time_ns() // 1_000_000),
        )
        EventSystem.emit(EventType.BOOKL1, bookl1)

    def _parse_mark_price(self, res: Dict[str, Any]):
        """
         {
            "e": "markPriceUpdate",     // Event type
            "E": 1562305380000,         // Event time
            "s": "BTCUSDT",             // Symbol
            "p": "11794.15000000",      // Mark price
            "i": "11784.62659091",      // Index price
            "P": "11784.25641265",      // Estimated Settle Price, only useful in the last hour before the settlement starts
            "r": "0.00038167",          // Funding rate
            "T": 1562306400000          // Next funding time
        }
        """
        id = res["s"] + self.market_type
        market = self._market_id[id]

        mark_price = MarkPrice(
            exchange=self._exchange_id,
            symbol=market["symbol"],
            price=float(res["p"]),
            timestamp=res.get("E", time.time_ns() // 1_000_000),
        )

        funding_rate = FundingRate(
            exchange=self._exchange_id,
            symbol=market["symbol"],
            rate=float(res["r"]),
            timestamp=res.get("E", time.time_ns() // 1_000_000),
            next_funding_time=res.get("T", time.time_ns() // 1_000_000),
        )

        index_price = IndexPrice(
            exchange=self._exchange_id,
            symbol=market["symbol"],
            price=float(res["i"]),
            timestamp=res.get("E", time.time_ns() // 1_000_000),
        )

        EventSystem.emit(EventType.MARK_PRICE, mark_price)
        EventSystem.emit(EventType.FUNDING_RATE, funding_rate)
        EventSystem.emit(EventType.INDEX_PRICE, index_price)

    def disconnect(self):
        self._ws_client.disconnect()


class BinancePrivateConnector:
    pass
