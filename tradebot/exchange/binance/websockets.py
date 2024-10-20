import time


from typing import Literal
from typing import Any, Dict


from asynciolimiter import Limiter


from tradebot.types import BookL1, Trade, Kline, MarkPrice, FundingRate, IndexPrice
from tradebot.entity import EventSystem
from tradebot.base import WSManager


from tradebot.exchange.binance.rest_api import BinanceRestApi
from tradebot.exchange.binance.constants import STREAM_URLS
from tradebot.exchange.binance.constants import AccountType, EventType


class BinanceWSManager(WSManager):
    def __init__(self, account_type: AccountType, api_key: str = None, secret: str = None):
        url = STREAM_URLS[account_type]
        super().__init__(url, limiter=Limiter(3 / 1))
        self._get_market_type(account_type)
        self._account_type = account_type
        self._rest_api = BinanceRestApi(account_type=account_type, api_key=api_key, secret=secret)
        self._exchange_id = "binance"
        self._market_id = self._rest_api.market_id

    def _get_market_type(self, account_type: AccountType):
        if account_type == AccountType.SPOT or account_type == AccountType.SPOT_TESTNET:
            self._market_type = "_spot"
        elif (
            account_type == AccountType.USD_M_FUTURE
            or account_type == AccountType.USD_M_FUTURE_TESTNET
        ):
            self._market_type = "_swap"
        else:
            self._market_type = ""

    async def subscribe_kline(
        self,
        symbol: str,
        interval: Literal[
            "1s",
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "1h",
            "2h",
            "4h",
            "6h",
            "8h",
            "12h",
            "1d",
            "3d",
            "1w",
            "1M",
        ],
    ):
        subscription_id = f"kline.{symbol}.{interval}"
        if subscription_id not in self._subscriptions:
            await self._limiter.wait()
            id = time.time_ns() // 1_000_000
            payload = {
                "method": "SUBSCRIBE",
                "params": [f"{symbol.lower()}@kline_{interval}"],
                "id": id,
            }
            self._subscriptions[subscription_id] = payload
            self._send(payload)
        else:
            self._log.info(f"Already subscribed to {subscription_id}")

    async def subscribe_book_ticker(self, symbol):
        subscription_id = f"book_ticker.{symbol}"
        if subscription_id not in self._subscriptions:
            await self._limiter.wait()
            id = time.time_ns() // 1_000_000
            payload = {
                "method": "SUBSCRIBE",
                "params": [f"{symbol.lower()}@bookTicker"],
                "id": id,
            }
            self._subscriptions[subscription_id] = payload
            self._send(payload)
        else:
            self._log.info(f"Already subscribed to {subscription_id}")

    async def subscribe_trade(self, symbol):
        subscription_id = f"trade.{symbol}"
        if subscription_id not in self._subscriptions:
            await self._limiter.wait()
            id = time.time_ns() // 1_000_000
            payload = {
                "method": "SUBSCRIBE",
                "params": [f"{symbol.lower()}@trade"],
                "id": id,
            }
            self._subscriptions[subscription_id] = payload
            self._send(payload)
        else:
            self._log.info(f"Already subscribed to {subscription_id}")

    async def subscribe_mark_price(self, symbol, interval: Literal["1s", "3s"] = "1s"):
        if self._market_type == "_spot":
            raise ValueError("Spot market doesn't have mark price")
        subscription_id = f"mark_price.{symbol}"
        if subscription_id not in self._subscriptions:
            await self._limiter.wait()
            id = time.time_ns() // 1_000_000
            payload = {
                "method": "SUBSCRIBE",
                "params": [f"{symbol.lower()}@markPrice@{interval}"],
                "id": id,
            }
            self._subscriptions[subscription_id] = payload
            self._send(payload)
        else:
            self._log.info(f"Already subscribed to {subscription_id}")

    async def subscribe_user_data_stream(self):
        subscription_id = f"user_data_stream.{self._account_type}"
        if subscription_id not in self._subscriptions:
            await self._limiter.wait()
            listen_key = await self._get_listen_key()
            id = time.time_ns() // 1_000_000
            payload = {
                "method": "SUBSCRIBE",
                "params": [listen_key],
                "id": id,
            }
            self._subscriptions[subscription_id] = payload
            self._send(payload)
        else:
            self._log.info(f"Already subscribed to {subscription_id}")

    async def _get_listen_key(self):
        try:
            res = await self._rest_api.start_user_data_stream()
            return res["listenKey"]
        except Exception as e:
            self._log.error(f"Failed to get listen key: {str(e)}")
            return None

    def _callback(self, msg):
        # self._log.info(str(msg))
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
            self._parse_book_ticker(
                msg
            )  # spot book ticker doesn't have "e" key. FUCK BINANCE

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
        id = res["s"] + self._market_type
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
        id = res["s"] + self._market_type
        market = self._market_id[id]

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
        id = res["s"] + self._market_type
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
        id = res["s"] + self._market_type
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
