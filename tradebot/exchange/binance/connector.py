import asyncio
import msgspec
from typing import Dict, Any
from decimal import Decimal
from tradebot.base import PublicConnector, PrivateConnector
from tradebot.constants import (
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
    TimeInForce,
)
from tradebot.schema import Order
from tradebot.schema import BookL1, Trade, Kline, MarkPrice, FundingRate, IndexPrice
from tradebot.exchange.binance.schema import BinanceMarket
from tradebot.exchange.binance.rest_api import BinanceApiClient
from tradebot.exchange.binance.constants import BinanceAccountType
from tradebot.exchange.binance.websockets import BinanceWSClient
from tradebot.exchange.binance.exchange import BinanceExchangeManager
from tradebot.exchange.binance.constants import (
    BinanceWsEventType,
    BinanceUserDataStreamWsEventType,
    BinanceBusinessUnit,
    BinanceEnumParser,
    BinanceOrderType,
)
from tradebot.exchange.binance.schema import (
    BinanceWsMessageGeneral,
    BinanceTradeData,
    BinanceSpotBookTicker,
    BinanceFuturesBookTicker,
    BinanceKline,
    BinanceMarkPrice,
    BinanceUserDataStreamMsg,
    BinanceSpotOrderUpdateMsg,
    BinanceFuturesOrderUpdateMsg,
)
from tradebot.core.nautilius_core import MessageBus
from tradebot.core.entity import TaskManager, RateLimit


class BinancePublicConnector(PublicConnector):
    _ws_client: BinanceWSClient
    _account_type: BinanceAccountType
    _market: Dict[str, BinanceMarket]
    _market_id: Dict[str, str]

    def __init__(
        self,
        account_type: BinanceAccountType,
        exchange: BinanceExchangeManager,
        msgbus: MessageBus,
        task_manager: TaskManager,
    ):
        if not account_type.is_spot and not account_type.is_future:
            raise ValueError(
                f"BinanceAccountType.{account_type.value} is not supported for Binance Public Connector"
            )

        super().__init__(
            account_type=account_type,
            market=exchange.market,
            market_id=exchange.market_id,
            exchange_id=exchange.exchange_id,
            ws_client=BinanceWSClient(
                account_type=account_type,
                handler=self._ws_msg_handler,
                task_manager=task_manager,
            ),
            msgbus=msgbus,
        )

        self._ws_general_decoder = msgspec.json.Decoder(BinanceWsMessageGeneral)
        self._ws_trade_decoder = msgspec.json.Decoder(BinanceTradeData)
        self._ws_spot_book_ticker_decoder = msgspec.json.Decoder(BinanceSpotBookTicker)
        self._ws_futures_book_ticker_decoder = msgspec.json.Decoder(
            BinanceFuturesBookTicker
        )
        self._ws_kline_decoder = msgspec.json.Decoder(BinanceKline)
        self._ws_mark_price_decoder = msgspec.json.Decoder(BinanceMarkPrice)

    @property
    def market_type(self):
        if self._account_type.is_spot:
            return "_spot"
        elif self._account_type.is_linear:
            return "_linear"
        elif self._account_type.is_inverse:
            return "_inverse"
        else:
            raise ValueError(
                f"Unsupported BinanceAccountType.{self._account_type.value}"
            )

    async def subscribe_trade(self, symbol: str):
        market = self._market.get(symbol, None)
        symbol = market.id if market else symbol
        await self._ws_client.subscribe_trade(symbol)

    async def subscribe_bookl1(self, symbol: str):
        market = self._market.get(symbol, None)
        symbol = market.id if market else symbol
        await self._ws_client.subscribe_book_ticker(symbol)

    async def subscribe_kline(self, symbol: str, interval: str):
        market = self._market.get(symbol, None)
        symbol = market.id if market else symbol
        await self._ws_client.subscribe_kline(symbol, interval)

    def _ws_msg_handler(self, raw: bytes):
        try:
            msg = self._ws_general_decoder.decode(raw)
            if msg.e:
                match msg.e:
                    case BinanceWsEventType.TRADE:
                        self._parse_trade(raw)
                    case BinanceWsEventType.BOOK_TICKER:
                        self._parse_futures_book_ticker(raw)
                    case BinanceWsEventType.KLINE:
                        self._parse_kline(raw)
                    case BinanceWsEventType.MARK_PRICE_UPDATE:
                        self._parse_mark_price(raw)
            elif msg.u:
                # spot book ticker doesn't have "e" key. FUCK BINANCE
                self._parse_spot_book_ticker(raw)
        except msgspec.DecodeError:
            self._log.error(f"Error decoding message: {str(raw)}")

    def _parse_kline(self, raw: bytes) -> Kline:
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
        res = self._ws_kline_decoder.decode(raw)
        id = res.s + self.market_type
        symbol = self._market_id[id]

        ticker = Kline(
            exchange=self._exchange_id,
            symbol=symbol,
            interval=res.k.i,
            open=float(res.k.o),
            high=float(res.k.h),
            low=float(res.k.l),
            close=float(res.k.c),
            volume=float(res.k.v),
            timestamp=res.E,
        )
        self._log.debug(f"{ticker}")
        self._msgbus.publish(topic="kline", msg=ticker)

    def _parse_trade(self, raw: bytes) -> Trade:
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

        res = self._ws_trade_decoder.decode(raw)

        id = res.s + self.market_type
        symbol = self._market_id[id]  # map exchange id to ccxt symbol

        trade = Trade(
            exchange=self._exchange_id,
            symbol=symbol,
            price=float(res.p),
            size=float(res.q),
            timestamp=res.T,
        )
        self._log.debug(f"{trade}")
        self._msgbus.publish(topic="trade", msg=trade)

    def _parse_spot_book_ticker(self, raw: bytes) -> BookL1:
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
        res = self._ws_spot_book_ticker_decoder.decode(raw)
        id = res.s + self.market_type
        symbol = self._market_id[id]

        bookl1 = BookL1(
            exchange=self._exchange_id,
            symbol=symbol,
            bid=float(res.b),
            ask=float(res.a),
            bid_size=float(res.B),
            ask_size=float(res.A),
            timestamp=self._clock.timestamp_ms(),
        )
        self._log.debug(f"{bookl1}")
        self._msgbus.publish(topic="bookl1", msg=bookl1)

    def _parse_futures_book_ticker(self, raw: bytes) -> BookL1:
        res = self._ws_futures_book_ticker_decoder.decode(raw)
        id = res.s + self.market_type
        symbol = self._market_id[id]
        bookl1 = BookL1(
            exchange=self._exchange_id,
            symbol=symbol,
            bid=float(res.b),
            ask=float(res.a),
            bid_size=float(res.B),
            ask_size=float(res.A),
            timestamp=res.E,
        )
        self._log.debug(f"{bookl1}")
        self._msgbus.publish(topic="bookl1", msg=bookl1)

    def _parse_mark_price(self, raw: bytes):
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
        res = self._ws_mark_price_decoder.decode(raw)
        id = res.s + self.market_type
        symbol = self._market_id[id]

        mark_price = MarkPrice(
            exchange=self._exchange_id,
            symbol=symbol,
            price=float(res.p),
            timestamp=res.E,
        )

        funding_rate = FundingRate(
            exchange=self._exchange_id,
            symbol=symbol,
            rate=float(res.r),
            timestamp=res.E,
            next_funding_time=res.T,
        )

        index_price = IndexPrice(
            exchange=self._exchange_id,
            symbol=symbol,
            price=float(res.i),
            timestamp=res.E,
        )
        self._log.debug(f"{mark_price}")
        self._log.debug(f"{funding_rate}")
        self._log.debug(f"{index_price}")
        self._msgbus.publish(topic="mark_price", msg=mark_price)
        self._msgbus.publish(topic="funding_rate", msg=funding_rate)
        self._msgbus.publish(topic="index_price", msg=index_price)


class BinancePrivateConnector(PrivateConnector):
    _ws_client: BinanceWSClient
    _account_type: BinanceAccountType
    _market: Dict[str, BinanceMarket]
    _market_id: Dict[str, str]
    _api_client: BinanceApiClient

    def __init__(
        self,
        account_type: BinanceAccountType,
        exchange: BinanceExchangeManager,
        msgbus: MessageBus,
        task_manager: TaskManager,
        rate_limit: RateLimit | None = None,
    ):
        super().__init__(
            account_type=account_type,
            market=exchange.market,
            market_id=exchange.market_id,
            exchange_id=exchange.exchange_id,
            ws_client=BinanceWSClient(
                account_type=account_type,
                handler=self._ws_msg_handler,
                task_manager=task_manager,
            ),
            api_client=BinanceApiClient(
                api_key=exchange.api_key,
                secret=exchange.secret,
                testnet=account_type.is_testnet,
            ),
            msgbus=msgbus,
            rate_limit=rate_limit,
        )

        self._task_manager = task_manager
        self._ws_msg_general_decoder = msgspec.json.Decoder(BinanceUserDataStreamMsg)
        self._ws_msg_spot_order_update_decoder = msgspec.json.Decoder(
            BinanceSpotOrderUpdateMsg
        )
        self._ws_msg_futures_order_update_decoder = msgspec.json.Decoder(
            BinanceFuturesOrderUpdateMsg
        )

    @property
    def market_type(self):
        if self._account_type.is_spot:
            return "_spot"
        elif self._account_type.is_linear:
            return "_linear"
        elif self._account_type.is_inverse:
            return "_inverse"

    async def _start_user_data_stream(self):
        if self._account_type.is_spot:
            res = await self._api_client.post_api_v3_user_data_stream()
        elif self._account_type.is_margin:
            res = await self._api_client.post_sapi_v1_user_data_stream()
        elif self._account_type.is_linear:
            res = await self._api_client.post_fapi_v1_listen_key()
        elif self._account_type.is_inverse:
            res = await self._api_client.post_dapi_v1_listen_key()
        elif self._account_type.is_portfolio_margin:
            res = await self._api_client.post_papi_v1_listen_key()
        return res.listenKey

    async def _keep_alive_listen_key(self, listen_key: str):
        if self._account_type.is_spot:
            await self._api_client.put_api_v3_user_data_stream(listen_key=listen_key)
        elif self._account_type.is_margin:
            await self._api_client.put_sapi_v1_user_data_stream(listen_key=listen_key)
        elif self._account_type.is_linear:
            await self._api_client.put_fapi_v1_listen_key()
        elif self._account_type.is_inverse:
            await self._api_client.put_dapi_v1_listen_key()
        elif self._account_type.is_portfolio_margin:
            await self._api_client.put_papi_v1_listen_key()

    async def _keep_alive_user_data_stream(
        self, listen_key: str, interval: int = 20, max_retry: int = 3
    ):
        retry_count = 0
        while retry_count < max_retry:
            await asyncio.sleep(60 * interval)
            try:
                await self._keep_alive_listen_key(listen_key)
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

    async def connect(self):
        await super().connect()
        listen_key = await self._start_user_data_stream()

        if listen_key:
            self._task_manager.create_task(
                self._keep_alive_user_data_stream(listen_key)
            )
            await self._ws_client.subscribe_user_data_stream(listen_key)
        else:
            raise RuntimeError("Failed to start user data stream")

    def _ws_msg_handler(self, raw: bytes):
        try:
            msg = self._ws_msg_general_decoder.decode(raw)
            if msg.e:
                match msg.e:
                    case BinanceUserDataStreamWsEventType.ORDER_TRADE_UPDATE:
                        self._parse_order_trade_update(raw)
                    case BinanceUserDataStreamWsEventType.EXECUTION_REPORT:
                        self._parse_execution_report(raw)
        except msgspec.DecodeError:
            self._log.error(f"Error decoding message: {str(raw)}")

    def _parse_order_trade_update(self, raw: bytes) -> Order:
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
        res = self._ws_msg_futures_order_update_decoder.decode(raw)

        event_data = res.o
        event_unit = res.fs

        # Only portfolio margin has "UM" and "CM" event business unit
        if event_unit == BinanceBusinessUnit.UM:
            id = event_data.s + "_linear"
            symbol = self._market_id[id]
        elif event_unit == BinanceBusinessUnit.CM:
            id = event_data.s + "_inverse"
            symbol = self._market_id[id]
        else:
            id = event_data.s + self.market_type
            symbol = self._market_id[id]

        # we use the last filled quantity to calculate the cost, instead of the accumulated filled quantity
        if (type := event_data.o) == BinanceOrderType.MARKET:
            cost = Decimal(event_data.l) * Decimal(event_data.ap)
            cum_cost = Decimal(event_data.z) * Decimal(event_data.ap)
        elif type == BinanceOrderType.LIMIT:
            price = Decimal(event_data.ap) or Decimal(
                event_data.p
            )  # if average price is 0 or empty, use price
            cost = Decimal(event_data.l) * price
            cum_cost = Decimal(event_data.z) * price

        order = Order(
            exchange=self._exchange_id,
            symbol=symbol,
            status=BinanceEnumParser.parse_order_status(event_data.X),
            id=event_data.i,
            amount=Decimal(event_data.q),
            filled=Decimal(event_data.z),
            client_order_id=event_data.c,
            timestamp=res.E,
            type=BinanceEnumParser.parse_order_type(event_data.o),
            side=BinanceEnumParser.parse_order_side(event_data.S),
            time_in_force=BinanceEnumParser.parse_time_in_force(event_data.f),
            price=float(event_data.p),
            average=float(event_data.ap),
            last_filled_price=float(event_data.L),
            last_filled=float(event_data.l),
            remaining=Decimal(event_data.q) - Decimal(event_data.z),
            fee=Decimal(event_data.n),
            fee_currency=event_data.N,
            cum_cost=cum_cost,
            cost=cost,
            reduce_only=event_data.R,
            position_side=BinanceEnumParser.parse_position_side(event_data.ps),
        )
        # order status can be "new", "partially_filled", "filled", "canceled", "expired", "failed"
        self._msgbus.publish(topic="binance.order", msg=order)

    def _parse_execution_report(self, raw: bytes) -> Order:
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
        event_data = self._ws_msg_spot_order_update_decoder.decode(raw)

        id = event_data.s + self.market_type
        symbol = self._market_id[id]

        order = Order(
            exchange=self._exchange_id,
            symbol=symbol,
            status=BinanceEnumParser.parse_order_status(event_data.X),
            id=event_data.i,
            amount=Decimal(event_data.q),
            filled=Decimal(event_data.z),
            client_order_id=event_data.c,
            timestamp=event_data.E,
            type=BinanceEnumParser.parse_order_type(event_data.o),
            side=BinanceEnumParser.parse_order_side(event_data.S),
            time_in_force=BinanceEnumParser.parse_time_in_force(event_data.f),
            price=float(event_data.p),
            last_filled_price=float(event_data.L),
            last_filled=float(event_data.l),
            remaining=Decimal(event_data.q) - Decimal(event_data.z),
            fee=Decimal(event_data.n),
            fee_currency=event_data.N,
            cum_cost=Decimal(event_data.Z),
            cost=Decimal(event_data.Y),
        )

        self._msgbus.publish(topic="binance.order", msg=order)

    async def _execute_order_request(
        self, market: BinanceMarket, symbol: str, params: Dict[str, Any]
    ):
        """Execute order request based on account type and market.

        Args:
            market: BinanceMarket object
            symbol: Trading symbol
            params: Order parameters

        Returns:
            API response

        Raises:
            ValueError: If market type is not supported for the account type
        """
        if self._account_type.is_spot:
            if not market.spot:
                raise ValueError(
                    f"BinanceAccountType.{self._account_type.value} is not supported for {symbol}"
                )
            return await self._api_client.post_api_v3_order(**params)

        elif self._account_type.is_isolated_margin_or_margin:
            if not market.margin:
                raise ValueError(
                    f"BinanceAccountType.{self._account_type.value} is not supported for {symbol}"
                )
            return await self._api_client.post_sapi_v1_margin_order(**params)

        elif self._account_type.is_linear:
            if not market.linear:
                raise ValueError(
                    f"BinanceAccountType.{self._account_type.value} is not supported for {symbol}"
                )
            return await self._api_client.post_fapi_v1_order(**params)

        elif self._account_type.is_inverse:
            if not market.inverse:
                raise ValueError(
                    f"BinanceAccountType.{self._account_type.value} is not supported for {symbol}"
                )
            return await self._api_client.post_dapi_v1_order(**params)

        elif self._account_type.is_portfolio_margin:
            if market.margin:
                return await self._api_client.post_papi_v1_margin_order(**params)
            elif market.linear:
                return await self._api_client.post_papi_v1_um_order(**params)
            elif market.inverse:
                return await self._api_client.post_papi_v1_cm_order(**params)

    async def create_order(
        self,
        symbol: str,
        side: OrderSide,
        type: OrderType,
        amount: Decimal,
        price: Decimal = None,
        time_in_force: TimeInForce = TimeInForce.GTC,
        position_side: PositionSide = None,
        **kwargs,
    ):
        if self._limiter:
            await self._limiter.acquire()
        market = self._market.get(symbol)
        if not market:
            raise ValueError(f"Symbol {symbol} formated wrongly, or not supported")
        symbol = market.id

        params = {
            "symbol": symbol,
            "side": BinanceEnumParser.to_binance_order_side(side).value,
            "type": BinanceEnumParser.to_binance_order_type(type).value,
            "quantity": amount,
        }

        if type == OrderType.LIMIT:
            if not price:
                raise ValueError("Price is required for  order")
            params["price"] = price
            params["timeInForce"] = BinanceEnumParser.to_binance_time_in_force(
                time_in_force
            ).value

        if position_side:
            params["positionSide"] = BinanceEnumParser.to_binance_position_side(
                position_side
            ).value

        reduce_only = kwargs.pop("reduceOnly", False) or kwargs.pop(
            "reduce_only", False
        )
        if reduce_only:
            params["reduceOnly"] = True

        params.update(kwargs)

        try:
            res = await self._execute_order_request(market, symbol, params)
            order = Order(
                exchange=self._exchange_id,
                symbol=symbol,
                status=OrderStatus.PENDING,
                id=res.orderId,
                amount=amount,
                filled=Decimal(0),
                client_order_id=res.clientOrderId,
                timestamp=res.updateTime,
                type=type,
                side=side,
                time_in_force=time_in_force,
                price=res.price if res.price else None,
                average=res.avgPrice if res.avgPrice else None,
                remaining=amount,
                reduce_only=res.reduceOnly if res.reduceOnly else None,
                position_side=BinanceEnumParser.parse_position_side(res.positionSide) if res.positionSide else None,
            )
            return order
        except Exception as e:
            self._log.error(f"Error creating order: {e} params: {str(params)}")
            order = Order(
                exchange=self._exchange_id,
                timestamp=self._clock.timestamp_ms(),
                symbol=symbol,
                type=type,
                side=side,
                amount=amount,
                price=float(price) if price else None,
                time_in_force=time_in_force,
                position_side=position_side,
                status=OrderStatus.FAILED,
                filled=Decimal(0),
                remaining=amount,
            )
            return order
    
    async def _execute_cancel_order_request(self, market: BinanceMarket, symbol: str, params: Dict[str, Any]):
        if self._account_type.is_spot:
            if not market.spot:
                raise ValueError(f"BinanceAccountType.{self._account_type.value} is not supported for {symbol}")
            return await self._api_client.delete_api_v3_order(**params)
        elif self._account_type.is_isolated_margin_or_margin:
            if not market.margin:
                raise ValueError(f"BinanceAccountType.{self._account_type.value} is not supported for {symbol}")
            return await self._api_client.delete_sapi_v1_margin_order(**params)
        elif self._account_type.is_linear:
            if not market.linear:
                raise ValueError(f"BinanceAccountType.{self._account_type.value} is not supported for {symbol}")
            return await self._api_client.delete_fapi_v1_order(**params)
        elif self._account_type.is_inverse:
            if not market.inverse:
                raise ValueError(f"BinanceAccountType.{self._account_type.value} is not supported for {symbol}")
            return await self._api_client.delete_dapi_v1_order(**params)
        elif self._account_type.is_portfolio_margin:
            if market.margin:
                return await self._api_client.delete_papi_v1_margin_order(**params)
            elif market.linear:
                return await self._api_client.delete_papi_v1_um_order(**params)
            elif market.inverse:
                return await self._api_client.delete_papi_v1_cm_order(**params)

    async def cancel_order(self, symbol: str, order_id: int, **kwargs):
        if self._limiter:
            await self._limiter.acquire()
        try:
            market = self._market.get(symbol)
            if not market:
                raise ValueError(f"Symbol {symbol} formated wrongly, or not supported")
            symbol = market.id

            params = {
                "symbol": symbol,
                "orderId": order_id,
                **kwargs,
            }

            res = await self._execute_cancel_order_request(market, symbol, params)
            order = Order(
                exchange=self._exchange_id,
                symbol=symbol,
                status=OrderStatus.CANCELING,
                id=res.orderId,
                amount=res.origQty,
                filled=Decimal(res.executedQty),
                client_order_id=res.clientOrderId,
                timestamp=res.updateTime,
                type=BinanceEnumParser.parse_order_type(res.type) if res.type else None,
                side=BinanceEnumParser.parse_order_side(res.side) if res.side else None,
                time_in_force=BinanceEnumParser.parse_time_in_force(res.timeInForce) if res.timeInForce else None,
                price=res.price,
                average=res.avgPrice,
                remaining=Decimal(res.origQty) - Decimal(res.executedQty),
                reduce_only=res.reduceOnly,
                position_side=BinanceEnumParser.parse_position_side(res.positionSide) if res.positionSide else None,
            )
            return order
        except Exception as e:
            self._log.error(f"Error canceling order: {e} params: {str(params)}")
            order = Order(
                exchange=self._exchange_id,
                timestamp=self._clock.timestamp_ms(),
                symbol=symbol,
                id=order_id,
                status=OrderStatus.FAILED,
            )
            return order
