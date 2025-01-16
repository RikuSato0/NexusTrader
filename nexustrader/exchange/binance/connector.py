import asyncio
import msgspec
from typing import Dict, Any
from decimal import Decimal
from nexustrader.base import PublicConnector, PrivateConnector
from nexustrader.constants import (
    OrderSide,
    OrderStatus,
    OrderType,
    PositionSide,
    TimeInForce,
)
from nexustrader.schema import Order
from nexustrader.schema import BookL1, Trade, Kline, MarkPrice, FundingRate, IndexPrice
from nexustrader.exchange.binance.schema import BinanceMarket
from nexustrader.exchange.binance.rest_api import BinanceApiClient
from nexustrader.exchange.binance.constants import BinanceAccountType
from nexustrader.exchange.binance.websockets import BinanceWSClient
from nexustrader.exchange.binance.exchange import BinanceExchangeManager
from nexustrader.exchange.binance.constants import (
    BinanceWsEventType,
    BinanceUserDataStreamWsEventType,
    BinanceBusinessUnit,
    BinanceEnumParser,
    BinanceOrderType,
)
from nexustrader.exchange.binance.schema import (
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
from nexustrader.core.cache import AsyncCache
from nexustrader.core.nautilius_core import MessageBus
from nexustrader.core.entity import TaskManager, RateLimit


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
        cache: AsyncCache,
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
            cache=cache,
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
