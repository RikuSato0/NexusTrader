import msgspec
from typing import Dict
from decimal import Decimal
from collections import defaultdict
from tradebot.base import PublicConnector, PrivateConnector, OrderManagerSystem
from tradebot.entity import EventSystem
from tradebot.types import BookL1, Order, Trade
from tradebot.constants import (
    EventType,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
    PositionSide,
)
from tradebot.exchange.bybit.types import (
    BybitWsMessageGeneral,
    BybitWsOrderMsg,
    BybitWsOrderbookDepthMsg,
    BybitOrderBook,
    BybitMarket,
    BybitWsTradeMsg,
)
from tradebot.entity import AsyncCache
from tradebot.exchange.bybit.rest_api import BybitApiClient
from tradebot.exchange.bybit.websockets import BybitWSClient
from tradebot.exchange.bybit.constants import (
    BybitAccountType,
    BybitEnumParser,
    BybitOrderType,
    BybitProductType,
)
from tradebot.exchange.bybit.exchange import BybitExchangeManager


class BybitPublicConnector(PublicConnector):
    _ws_client: BybitWSClient
    _account_type: BybitAccountType

    def __init__(
        self,
        account_type: BybitAccountType,
        exchange: BybitExchangeManager,
    ):
        if account_type in {BybitAccountType.ALL, BybitAccountType.ALL_TESTNET}:
            raise ValueError(
                f"Please not using `BybitAccountType.ALL` or `BybitAccountType.ALL_TESTNET` in `PublicConnector`"
            )

        super().__init__(
            account_type=account_type,
            market=exchange.market,
            market_id=exchange.market_id,
            exchange_id=exchange.exchange_id,
            ws_client=BybitWSClient(
                account_type=account_type, handler=self._ws_msg_handler
            ),
        )
        self._ws_client: BybitWSClient = self._ws_client
        self._ws_msg_trade_decoder = msgspec.json.Decoder(BybitWsTradeMsg)
        self._ws_msg_orderbook_decoder = msgspec.json.Decoder(BybitWsOrderbookDepthMsg)
        self._ws_msg_general_decoder = msgspec.json.Decoder(BybitWsMessageGeneral)

        self._orderbook = defaultdict(BybitOrderBook)

    @property
    def market_type(self):
        if self._account_type.is_spot:
            return "_spot"
        elif self._account_type.is_linear:
            return "_linear"
        elif self._account_type.is_inverse:
            return "_inverse"
        else:
            raise ValueError(f"Unsupported BybitAccountType.{self._account_type.value}")

    def _ws_msg_handler(self, raw: bytes):
        try:
            ws_msg: BybitWsMessageGeneral = self._ws_msg_general_decoder.decode(raw)
            if ws_msg.ret_msg == "pong":
                self._ws_client._transport.notify_user_specific_pong_received()
                self._log.debug(f"Pong received {str(ws_msg)}")
                return
            if ws_msg.success is False:
                self._log.error(f"WebSocket error: {ws_msg}")
                return

            if "orderbook" in ws_msg.topic:
                self._handle_orderbook(raw, ws_msg.topic)
            elif "publicTrade" in ws_msg.topic:
                self._handle_trade(raw)
            
        except msgspec.DecodeError:
            self._log.error(f"Error decoding message: {str(raw)}")
    
    def _handle_trade(self, raw: bytes):
        msg: BybitWsTradeMsg = self._ws_msg_trade_decoder.decode(raw)
        for d in msg.data:
            id = d.s + self.market_type
            market = self._market_id[id]
            symbol = market.symbol
            trade = Trade(
                exchange=self._exchange_id,
                symbol=symbol,
                price=float(d.p),
                size=float(d.v),
                timestamp=msg.ts,
            )
            EventSystem.emit(EventType.TRADE, trade)
            

    def _handle_orderbook(self, raw: bytes, topic: str):
        msg: BybitWsOrderbookDepthMsg = self._ws_msg_orderbook_decoder.decode(raw)
        id = msg.data.s + self.market_type
        market = self._market_id[id]
        symbol = market.symbol

        res = self._orderbook[symbol].parse_orderbook_depth(msg, levels=1)

        bid, bid_size = (
            (res["bids"][0][0], res["bids"][0][1]) if res["bids"] else (0, 0)
        )
        ask, ask_size = (
            (res["asks"][0][0], res["asks"][0][1]) if res["asks"] else (0, 0)
        )
        
        bookl1 = BookL1(
            exchange=self._exchange_id,
            symbol=symbol,
            timestamp=msg.ts,
            bid=bid,
            bid_size=bid_size,
            ask=ask,
            ask_size=ask_size,
        )
        EventSystem.emit(EventType.BOOKL1, bookl1)

    async def subscribe_bookl1(self, symbol: str):
        market = self._market.get(symbol, None)
        symbol = market.id if market else symbol
        await self._ws_client.subscribe_order_book(symbol, depth=1)

    async def subscribe_trade(self, symbol: str):
        market = self._market.get(symbol, None)
        symbol = market.id if market else symbol
        await self._ws_client.subscribe_trade(symbol)
        

    async def subscribe_kline(self, symbol: str, interval: str):
        pass


class BybitPrivateConnector(PrivateConnector):
    _ws_client: BybitWSClient
    _account_type: BybitAccountType
    _market: Dict[str, BybitMarket]
    _market_id: Dict[str, BybitMarket]

    def __init__(
        self,
        exchange: BybitExchangeManager,
        account_type: BybitAccountType,
        strategy_id: str = None,
        user_id: str = None,
        rate_limit: float = None,
    ):
        # all the private endpoints are the same for all account types, so no need to pass account_type
        # only need to determine if it's testnet or not

        if not exchange.api_key or not exchange.secret:
            raise ValueError("API key and secret are required for private endpoints")

        if account_type not in {BybitAccountType.ALL, BybitAccountType.ALL_TESTNET}:
            raise ValueError(
                "Please using `BybitAccountType.ALL` or `BybitAccountType.ALL_TESTNET` in `PrivateConnector`"
            )

        super().__init__(
            account_type=account_type,
            market=exchange.market,
            market_id=exchange.market_id,
            exchange_id=exchange.exchange_id,
            ws_client=BybitWSClient(
                account_type=account_type,
                handler=self._ws_msg_handler,
                api_key=exchange.api_key,
                secret=exchange.secret,
            ),
            cache=AsyncCache(
                account_type="BYBIT",
                strategy_id=strategy_id,
                user_id=user_id,
            ),
            rate_limit=rate_limit,
        )

        self._api_client = BybitApiClient(
            api_key=exchange.api_key,
            secret=exchange.secret,
            testnet=account_type.is_testnet,
        )

        self._oms = OrderManagerSystem(
            cache=self._cache,
        )

        self._ws_msg_general_decoder = msgspec.json.Decoder(BybitWsMessageGeneral)
        self._ws_msg_order_update_decoder = msgspec.json.Decoder(BybitWsOrderMsg)

    async def connect(self):
        await super().connect()
        self._task_manager.create_task(self._oms.handle_order_event())
        await self._ws_client.subscribe_order(topic="order")

    def _ws_msg_handler(self, raw: bytes):
        try:
            ws_msg = self._ws_msg_general_decoder.decode(raw)
            if ws_msg.op == "pong":
                self._ws_client._transport.notify_user_specific_pong_received()
                self._log.debug(f"Pong received {str(ws_msg)}")
                return
            if ws_msg.success is False:
                self._log.error(f"WebSocket error: {ws_msg}")
                return
            if "order" in ws_msg.topic:
                self._parse_order_update(raw)
        except msgspec.DecodeError:
            self._log.error(f"Error decoding message: {str(raw)}")

    def _get_category(self, market: BybitMarket):
        if market.spot:
            return "spot"
        elif market.linear:
            return "linear"
        elif market.inverse:
            return "inverse"
        else:
            raise ValueError(f"Unsupported market type: {market.type}")

    async def cancel_order(self, symbol: str, order_id: str, **kwargs):
        if self._limiter:
            await self._limiter.wait()
        try:
            market = self._market.get(symbol)
            if not market:
                raise ValueError(f"Symbol {symbol} formated wrongly, or not supported")
            symbol = market.id

            category = self._get_category(market)

            params = {
                "category": category,
                "symbol": symbol,
                "order_id": order_id,
                **kwargs,
            }

            res = await self._api_client.post_v5_order_cancel(**params)
            order = Order(
                exchange=self._exchange_id,
                id=res.result.orderId,
                client_order_id=res.result.orderLinkId,
                timestamp=res.time,
                symbol=market.symbol,
                status=OrderStatus.CANCELING,
            )
            self._oms.add_order_msg(order)
            return order
        except Exception as e:
            self._log.error(f"Error canceling order: {e} params: {str(params)}")
            order = Order(
                exchange=self._exchange_id,
                timestamp=self._clock.timestamp_ms(),
                symbol=symbol,
                status=OrderStatus.FAILED,
            )
            return order

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
            await self._limiter.wait()
        market = self._market.get(symbol)
        if not market:
            raise ValueError(f"Symbol {symbol} formated wrongly, or not supported")
        symbol = market.id

        category = self._get_category(market)

        params = {
            "category": category,
            "symbol": symbol,
            "order_type": BybitEnumParser.to_bybit_order_type(type).value,
            "side": BybitEnumParser.to_bybit_order_side(side).value,
            "qty": str(amount),
        }

        if type == OrderType.LIMIT:
            params["price"] = str(price)
            params["timeInForce"] = BybitEnumParser.to_bybit_time_in_force(
                time_in_force
            ).value

        if position_side:
            params["positionSide"] = BybitEnumParser.to_bybit_position_side(
                position_side
            ).value

        params.update(kwargs)

        try:
            res = await self._api_client.post_v5_order_create(**params)

            order = Order(
                exchange=self._exchange_id,
                id=res.result.orderId,
                client_order_id=res.result.orderLinkId,
                timestamp=int(res.time),
                symbol=market.symbol,
                type=type,
                side=side,
                amount=amount,
                price=float(price),
                time_in_force=time_in_force,
                position_side=position_side,
                status=OrderStatus.PENDING,
                filled=Decimal(0),
                remaining=amount,
            )
            self._oms.add_order_msg(order)
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
                price=float(price),
                time_in_force=time_in_force,
                position_side=position_side,
                status=OrderStatus.FAILED,
                filled=Decimal(0),
                remaining=amount,
            )
            return order

    def _parse_order_update(self, raw: bytes):
        order_msg = self._ws_msg_order_update_decoder.decode(raw)
        for data in order_msg.data:
            category = data.category
            if category == BybitProductType.SPOT:
                id = data.symbol + "_spot"
            elif category == BybitProductType.LINEAR:
                id = data.symbol + "_linear"
            elif category == BybitProductType.INVERSE:
                id = data.symbol + "_inverse"
            market = self._market_id[id]

            order = Order(
                exchange=self._exchange_id,
                symbol=market.symbol,
                status=BybitEnumParser.parse_order_status(data.orderStatus),
                id=data.orderId,
                client_order_id=data.orderLinkId,
                timestamp=int(data.updatedTime),
                type=BybitEnumParser.parse_order_type(data.orderType),
                side=BybitEnumParser.parse_order_side(data.side),
                time_in_force=BybitEnumParser.parse_time_in_force(data.timeInForce),
                price=float(data.price),
                average=float(data.avgPrice) if data.avgPrice else None,
                amount=Decimal(data.qty),
                filled=Decimal(data.cumExecQty),
                remaining=Decimal(data.leavesQty),
                fee=float(data.cumExecFee),
                fee_currency=data.feeCurrency,
                cum_cost=float(data.cumExecValue),
                reduce_only=data.reduceOnly,
                position_side=BybitEnumParser.parse_position_side(data.positionIdx),
            )

            self._oms.add_order_msg(order)

    async def disconnect(self):
        await super().disconnect()
        await self._api_client.close_session()
