import time
import asyncio

from typing import Literal
from typing import Any, Dict
from decimal import Decimal

from asynciolimiter import Limiter


from tradebot.types import (
    BookL1,
    Trade,
    Kline,
    MarkPrice,
    FundingRate,
    IndexPrice,
    Order,
)
from tradebot.entity import EventSystem
from tradebot.base import WSManager
from tradebot.constants import EventType


from tradebot.exchange.binance.rest_api import BinanceRestApi
from tradebot.exchange.binance.constants import STREAM_URLS
from tradebot.exchange.binance.constants import BinanceAccountType


class BinanceWSManager(WSManager):
    def __init__(
        self,
        account_type: BinanceAccountType,
        market: Dict[str, Any],
        market_id: Dict[str, Any],
        api_key: str = None,
        secret: str = None,
    ):
        url = STREAM_URLS[account_type]
        super().__init__(url, limiter=Limiter(3 / 1))
        self._get_market_type(account_type)
        self._account_type = account_type
        self._rest_api = BinanceRestApi(
            account_type=account_type, api_key=api_key, secret=secret
        )
        self._exchange_id = "binance"
        self._market_id = market_id
        self._market = market

    def _get_market_type(self, account_type: BinanceAccountType):
        if (
            account_type == BinanceAccountType.SPOT
            or account_type == BinanceAccountType.SPOT_TESTNET
            or account_type == BinanceAccountType.MARGIN
            or account_type == BinanceAccountType.ISOLATED_MARGIN
        ):
            self._market_type = "_spot"
        elif (
            account_type == BinanceAccountType.USD_M_FUTURE
            or account_type == BinanceAccountType.USD_M_FUTURE_TESTNET
        ):
            self._market_type = "_linear"
        elif (
            account_type == BinanceAccountType.COIN_M_FUTURE
            or account_type == BinanceAccountType.COIN_M_FUTURE_TESTNET
        ):
            self._market_type = "_inverse"

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
        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol
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

    async def subscribe_book_l1(self, symbol):
        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol
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
        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol
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
        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol
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
            asyncio.create_task(self._keep_alive_user_data_stream(listen_key))
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

    async def _keep_alive_user_data_stream(
        self, listen_key: str, interval: int = 20, max_retry: int = 3
    ):
        retry_count = 0
        while retry_count < max_retry:
            await asyncio.sleep(60 * interval)
            try:
                await self._rest_api.keep_alive_user_data_stream(listen_key)
                retry_count = 0  # Reset retry count on successful keep-alive
            except Exception as e:
                self._log.error(f"Failed to keep alive listen key: {str(e)}")
                retry_count += 1
                if retry_count < max_retry:
                    await asyncio.sleep(5)
                else:
                    self._log.error(
                        f"Max retries ({max_retry}) reached. Stopping keep-alive attempts."
                    )
                    break
    
    async def _resubscribe(self):
        for _, payload in self._subscriptions.items():
            await self._limiter.wait()
            self._send(payload)
    
    def _callback(self, msg):
        # if self._is_user_data_stream:
        #     match msg["e"]:
        #         case "ORDER_TRADE_UPDATE":
        #             self._parse_order_trade_update(msg)
        #         case "executionReport":
        #             self._parse_execution_report(msg)
        #     return

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
                case "ORDER_TRADE_UPDATE":
                    self._parse_order_trade_update(msg)
                case "executionReport":
                    self._parse_execution_report(msg)

        elif "u" in msg:
            # spot book ticker doesn't have "e" key. FUCK BINANCE
            self._parse_book_ticker(msg)

    def _parse_order_trade_update(self, res: Dict[str, Any]) -> Order:
        """
        {
            "e": "ORDER_TRADE_UPDATE", // Event type
            "T": 1727352962757,  // Transaction time
            "E": 1727352962762, // Event time
            "fs": "UM", // Event business unit. 'UM' for USDS-M futures and 'CM' for COIN-M futures
            "o": {
                "s": "NOTUSDT", // Symbol
                "c": "c-11WLU7VP1727352880uzcu2rj4ss0i", // Client order ID
                "S": "SELL", // Side
                "o": "LIMIT", // Order type
                "f": "GTC", // Time in force
                "q": "5488", // Original quantity
                "p": "0.0084830", // Original price
                "ap": "0", // Average price
                "sp": "0", // Ignore
                "x": "NEW", // Execution type
                "X": "NEW", // Order status
                "i": 4968510801, // Order ID
                "l": "0", // Order last filled quantity
                "z": "0", // Order filled accumulated quantity
                "L": "0", // Last filled price
                "n": "0", // Commission, will not be returned if no commission
                "N": "USDT", // Commission asset, will not be returned if no commission
                "T": 1727352962757, // Order trade time
                "t": 0, // Trade ID
                "b": "0", // Bids Notional
                "a": "46.6067521", // Ask Notional
                "m": false, // Is this trade the maker side?
                "R": false, // Is this reduce only
                "ps": "BOTH", // Position side
                "rp": "0", // Realized profit of the trade
                "V": "EXPIRE_NONE", // STP mode
                "pm": "PM_NONE",
                "gtd": 0
            }
        }
        """
        event_data = res["o"]
        event_unit = res.get("fs", "")

        # Only portfolio margin has "UM" and "CM" event business unit
        if event_unit == "UM":
            id = event_data["s"] + "_linear"
            market = self._market_id[id]
        elif event_unit == "CM":
            id = event_data["s"] + "_inverse"
            market = self._market_id[id]
        else:
            id = event_data["s"] + self._market_type
            market = self._market_id[id]

        # we use the last filled quantity to calculate the cost, instead of the accumulated filled quantity
        if (type := event_data["o"].lower()) == "market":
            cost = float(event_data.get("l", "0")) * float(event_data.get("ap", "0"))
        elif type == "limit":
            price = float(event_data.get("ap", "0")) or float(
                event_data.get("p", "0")
            )  # if average price is 0 or empty, use price
            cost = float(event_data.get("l", "0")) * price

        order = Order(
            raw=event_data,
            success=True,
            exchange="binance",
            id=event_data.get("i", None),
            client_order_id=event_data.get("c", None),
            timestamp=event_data.get("T", None),
            symbol=market["symbol"],
            type=type,
            side=event_data.get("S", "").lower(),
            status=event_data.get("X", "").lower(),
            price=event_data.get("p", None),
            average=event_data.get("ap", None),
            last_filled_price=event_data.get("L", None),
            amount=event_data.get("q", None),
            filled=event_data.get("z", None),
            last_filled=event_data.get("l", None),
            remaining=Decimal(event_data["q"]) - Decimal(event_data["z"]),
            fee=event_data.get("n", None),
            fee_currency=event_data.get("N", None),
            cost=cost,
            last_trade_timestamp=event_data.get("T", None),
            reduce_only=event_data.get("R", None),
            position_side=event_data.get("ps", "").lower(),
            time_in_force=event_data.get("f", None),
        )
        # order status can be "new", "partially_filled", "filled", "canceled", "expired", "failed"
        EventSystem.emit(order.status, order)

    def _parse_execution_report(self, event_data: Dict[str, Any]) -> Order:
        """
        {
            "e": "executionReport", // Event type
            "E": 1727353057267, // Event time
            "s": "ORDIUSDT", // Symbol
            "c": "c-11WLU7VP2rj4ss0i", // Client order ID
            "S": "BUY", // Side
            "o": "MARKET", // Order type
            "f": "GTC", // Time in force
            "q": "0.50000000", // Order quantity
            "p": "0.00000000", // Order price
            "P": "0.00000000", // Stop price
            "g": -1, // Order list id
            "x": "TRADE", // Execution type
            "X": "PARTIALLY_FILLED", // Order status
            "i": 2233880350, // Order ID
            "l": "0.17000000", // last executed quantity
            "z": "0.17000000", // Cumulative filled quantity
            "L": "36.88000000", // Last executed price
            "n": "0.00000216", // Commission amount
            "N": "BNB", // Commission asset
            "T": 1727353057266, // Transaction time
            "t": 105069149, // Trade ID
            "w": false, // Is the order on the book?
            "m": false, // Is this trade the maker side?
            "O": 1727353057266, // Order creation time
            "Z": "6.26960000", // Cumulative quote asset transacted quantity
            "Y": "6.26960000", // Last quote asset transacted quantity (i.e. lastPrice * lastQty)
            "V": "EXPIRE_MAKER", // Self trade prevention Mode
            "I": 1495839281094 // Ignore
        }

        # Example of an execution report event for a partially filled market buy order
        {
            "e": "executionReport", // Event type
            "E": 1727353057267, // Event time
            "s": "ORDIUSDT", // Symbol
            "c": "c-11WLU7VP2rj4ss0i", // Client order ID
            "S": "BUY", // Side
            "o": "MARKET", // Order type
            "f": "GTC", // Time in force
            "q": "0.50000000", // Order quantity
            "p": "0.00000000", // Order price
            "P": "0.00000000", // Stop price
            "g": -1, // Order list id
            "x": "TRADE", // Execution type
            "X": "PARTIALLY_FILLED", // Order status
            "i": 2233880350, // Order ID
            "l": "0.17000000", // last executed quantity
            "z": "0.34000000", // Cumulative filled quantity
            "L": "36.88000000", // Last executed price
            "n": "0.00000216", // Commission amount
            "N": "BNB", // Commission asset
            "T": 1727353057266, // Transaction time
            "t": 105069150, // Trade ID
            "w": false, // Is the order on the book?
            "m": false, // Is this trade the maker side?
            "O": 1727353057266, // Order creation time
            "Z": "12.53920000", // Cumulative quote asset transacted quantity
            "Y": "6.26960000", // Last quote asset transacted quantity (i.e. lastPrice * lastQty)
            "V": "EXPIRE_MAKER", // Self trade prevention Mode
            "I": 1495839281094 // Ignore
        }
        """
        id = event_data["s"] + self._market_type
        market = self._market_id[id]
        order = Order(
            raw=event_data,
            success=True,
            exchange="binance",
            id=event_data.get("i", None),
            client_order_id=event_data.get("c", None),
            timestamp=event_data.get("T", None),
            symbol=market["symbol"],
            type=event_data.get("o", "").lower(),
            side=event_data.get("S", "").lower(),
            status=event_data.get("X", "").lower(),
            price=event_data.get("p", None),
            average=event_data.get("ap", None),
            last_filled_price=event_data.get("L", None),
            amount=event_data.get("q", None),
            filled=event_data.get("z", None),
            last_filled=event_data.get("l", None),
            remaining=Decimal(event_data.get("q", "0"))
            - Decimal(event_data.get("z", "0")),
            fee=event_data.get("n", None),
            fee_currency=event_data.get("N", None),
            cost=event_data.get("Y", None),
            last_trade_timestamp=event_data.get("T", None),
            time_in_force=event_data.get("f", None),
        )
        EventSystem.emit(order.status, order)

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
