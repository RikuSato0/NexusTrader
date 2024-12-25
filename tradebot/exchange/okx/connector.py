import msgspec
from typing import Dict
from decimal import Decimal
from tradebot.exchange.okx import OkxAccountType
from tradebot.exchange.okx.websockets import OkxWSClient
from tradebot.exchange.okx.exchange import OkxExchangeManager
from tradebot.exchange.okx.schema import OkxWsGeneralMsg
from tradebot.schema import Trade, BookL1, Kline, Order
from tradebot.exchange.okx.schema import (
    OkxMarket,
    OkxWsBboTbtMsg,
    OkxWsCandleMsg,
    OkxWsTradeMsg,
    OkxWsOrderMsg,
)
from tradebot.constants import (
    OrderStatus,
    TimeInForce,
    PositionSide,
)
from tradebot.base import PublicConnector, PrivateConnector
from tradebot.core.nautilius_core import MessageBus
from tradebot.core.entity import TaskManager, RateLimit
from tradebot.exchange.okx.rest_api import OkxApiClient
from tradebot.constants import OrderSide, OrderType
from tradebot.exchange.okx.constants import (
    OkxTdMode,
    OkxEnumParser,
)


class OkxPublicConnector(PublicConnector):
    _ws_client: OkxWSClient
    _account_type: OkxAccountType

    def __init__(
        self,
        account_type: OkxAccountType,
        exchange: OkxExchangeManager,
        msgbus: MessageBus,
        task_manager: TaskManager,
    ):
        super().__init__(
            account_type=account_type,
            market=exchange.market,
            market_id=exchange.market_id,
            exchange_id=exchange.exchange_id,
            ws_client=OkxWSClient(
                account_type=account_type,
                handler=self._ws_msg_handler,
                task_manager=task_manager,
            ),
            msgbus=msgbus,
        )

        self._ws_msg_general_decoder = msgspec.json.Decoder(OkxWsGeneralMsg)
        self._ws_msg_bbo_tbt_decoder = msgspec.json.Decoder(OkxWsBboTbtMsg)
        self._ws_msg_candle_decoder = msgspec.json.Decoder(OkxWsCandleMsg)
        self._ws_msg_trade_decoder = msgspec.json.Decoder(OkxWsTradeMsg)

    async def subscribe_trade(self, symbol: str):
        market = self._market.get(symbol, None)
        if not market:
            raise ValueError(f"Symbol {symbol} not found in market")
        await self._ws_client.subscribe_trade(market.id)

    async def subscribe_bookl1(self, symbol: str):
        market = self._market.get(symbol, None)
        if not market:
            raise ValueError(f"Symbol {symbol} not found in market")
        await self._ws_client.subscribe_order_book(market.id, channel="bbo-tbt")

    async def subscribe_kline(self, symbol: str, interval: str):
        market = self._market.get(symbol, None)
        if not market:
            raise ValueError(f"Symbol {symbol} not found in market")
        await self._ws_client.subscribe_candlesticks(market.id, interval)

    def _ws_msg_handler(self, raw: bytes):
        if raw == b"pong":
            self._ws_client._transport.notify_user_specific_pong_received()
            self._log.debug(f"Pong received:{str(raw)}")
            return
        try:
            ws_msg: OkxWsGeneralMsg = self._ws_msg_general_decoder.decode(raw)
            if ws_msg.is_event_msg:
                self._handle_event_msg(ws_msg)
            else:
                channel: str = ws_msg.arg.channel
                if channel == "bbo-tbt":
                    self._handle_bbo_tbt(raw)
                elif channel == "trades":
                    self._handle_trade(raw)
                elif channel.startswith("candle"):
                    self._handle_kline(raw)
        except msgspec.DecodeError:
            self._log.error(f"Error decoding message: {str(raw)}")

    def _handle_event_msg(self, ws_msg: OkxWsGeneralMsg):
        if ws_msg.event == "error":
            self._log.error(f"Error code: {ws_msg.code}, message: {ws_msg.msg}")
        elif ws_msg.event == "login":
            self._log.debug("Login success")
        elif ws_msg.event == "subscribe":
            self._log.debug(f"Subscribed to {ws_msg.arg.channel}")

    def _handle_kline(self, raw: bytes):
        """
        {
            "arg": {
                "channel": "candle1D",
                "instId": "BTC-USDT"
            },
            "data": [
                [
                "1597026383085", ts
                "8533.02", open
                "8553.74", high
                "8527.17", low
                "8548.26", close
                "45247", vol
                "529.5858061",
                "5529.5858061",
                "0"
                ]
            ]
            }
        """
        msg: OkxWsCandleMsg = self._ws_msg_candle_decoder.decode(raw)

        id = msg.arg.instId
        symbol = self._market_id[id]

        for d in msg.data:
            kline = Kline(
                exchange=self._exchange_id,
                symbol=symbol,
                interval=msg.arg.channel,
                open=float(d[1]),
                high=float(d[2]),
                low=float(d[3]),
                close=float(d[4]),
                volume=float(d[5]),
                timestamp=int(d[0]),
            )
            self._msgbus.publish(topic="kline", msg=kline)

    def _handle_trade(self, raw: bytes):
        """
        {
            "arg": {
                "channel": "trades",
                "instId": "BTC-USD-191227"
            },
            "data": [
                {
                    "instId": "BTC-USD-191227",
                    "tradeId": "9",
                    "px": "0.016",
                    "sz": "50",
                    "side": "buy",
                    "ts": "1597026383085"
                }
            ]
        }
        """
        msg: OkxWsTradeMsg = self._ws_msg_trade_decoder.decode(raw)
        id = msg.arg.instId
        symbol = self._market_id[id]
        for d in msg.data:
            trade = Trade(
                exchange=self._exchange_id,
                symbol=symbol,
                price=float(d.px),
                size=float(d.sz),
                timestamp=int(d.ts),
            )
            self._msgbus.publish(topic="trade", msg=trade)

    def _handle_bbo_tbt(self, raw: bytes):
        """
        {
            'arg': {
                'channel': 'bbo-tbt',
                'instId': 'BTC-USDT'
            },
            'data': [{
                'asks': [['67201.2', '2.17537208', '0', '7']],
                'bids': [['67201.1', '1.44375999', '0', '5']],
                'ts': '1729594943707',
                'seqId': 34209632254
            }]
        }
        """
        msg: OkxWsBboTbtMsg = self._ws_msg_bbo_tbt_decoder.decode(raw)

        id = msg.arg.instId
        symbol = self._market_id[id]

        for d in msg.data:
            bookl1 = BookL1(
                exchange=self._exchange_id,
                symbol=symbol,
                bid=float(d.bids[0][0]),
                ask=float(d.asks[0][0]),
                bid_size=float(d.bids[0][1]),
                ask_size=float(d.asks[0][1]),
                timestamp=int(d.ts),
            )
            self._msgbus.publish(topic="bookl1", msg=bookl1)


class OkxPrivateConnector(PrivateConnector):
    _ws_client: OkxWSClient
    _api_client: OkxApiClient
    _account_type: OkxAccountType
    _market: Dict[str, OkxMarket]
    _market_id: Dict[str, str]

    def __init__(
        self,
        exchange: OkxExchangeManager,
        account_type: OkxAccountType,
        msgbus: MessageBus,
        task_manager: TaskManager,
        rate_limit: RateLimit | None = None,
    ):
        if not exchange.api_key or not exchange.secret or not exchange.passphrase:
            raise ValueError(
                "API key, secret, and passphrase are required for private endpoints"
            )

        super().__init__(
            account_type=account_type,
            market=exchange.market,
            market_id=exchange.market_id,
            exchange_id=exchange.exchange_id,
            ws_client=OkxWSClient(
                account_type=account_type,
                handler=self._ws_msg_handler,
                task_manager=task_manager,
                api_key=exchange.api_key,
                secret=exchange.secret,
                passphrase=exchange.passphrase,
            ),
            api_client=OkxApiClient(
                api_key=exchange.api_key,
                secret=exchange.secret,
                passphrase=exchange.passphrase,
                testnet=account_type.is_testnet,
            ),
            msgbus=msgbus,
            rate_limit=rate_limit,
        )

        self._decoder_ws_general_msg = msgspec.json.Decoder(OkxWsGeneralMsg)
        self._decoder_ws_order_msg = msgspec.json.Decoder(OkxWsOrderMsg, strict=False)
    
    async def connect(self):
        await self._ws_client.subscribe_orders()

    def _handle_event_msg(self, msg: OkxWsGeneralMsg):
        if msg.event == "error":
            self._log.error(msg)
        elif msg.event == "login":
            self._log.info("Login success")
        elif msg.event == "subscribe":
            self._log.info(f"Subscribed to {msg.arg.channel}")

    def _ws_msg_handler(self, raw: bytes):
        if raw == b"pong":
            self._ws_client._transport.notify_user_specific_pong_received()
            self._log.debug(f"Pong received: {str(raw)}")
            return
        try:
            ws_msg: OkxWsGeneralMsg = self._decoder_ws_general_msg.decode(raw)
            if ws_msg.is_event_msg:
                self._handle_event_msg(ws_msg)
            else:
                channel = ws_msg.arg.channel
                if channel == "orders":
                    self._handle_orders(raw)
                elif channel == "positions":
                    self._handle_positions(raw)
                elif channel == "account":
                    self._handle_account(raw)
                elif channel == "fills":
                    self._handle_fills(raw)
        except msgspec.DecodeError as e:
            self._log.error(f"Error decoding message: {str(raw)} {e}")

    def _handle_orders(self, raw: bytes):
        msg: OkxWsOrderMsg = self._decoder_ws_order_msg.decode(raw)
        self._log.debug(f"Order update: {str(msg)}")
        for data in msg.data:
            symbol = self._market_id[data.instId]
            order = Order(
                exchange=self._exchange_id,
                symbol=symbol,
                status=OkxEnumParser.parse_order_status(data.state),
                id=data.ordId,
                amount=Decimal(data.sz),
                filled=Decimal(data.accFillSz),
                client_order_id=data.clOrdId,
                timestamp=data.uTime,
                type=OkxEnumParser.parse_order_type(data.ordType),
                side=OkxEnumParser.parse_order_side(data.side),
                time_in_force=OkxEnumParser.parse_time_in_force(data.ordType),
                price=float(data.px) if data.px else None,
                average=float(data.avgPx) if data.avgPx else None,
                last_filled_price=float(data.fillPx) if data.fillPx else None,
                last_filled=Decimal(data.fillSz) if data.fillSz else Decimal(0),
                remaining=Decimal(data.sz) - Decimal(data.accFillSz),
                fee=Decimal(data.fee),
                fee_currency=data.feeCcy,
                cost=Decimal(data.avgPx) * Decimal(data.fillSz),
                cum_cost=Decimal(data.avgPx) * Decimal(data.accFillSz),
                reduce_only=data.reduceOnly,
                position_side=OkxEnumParser.parse_position_side(data.posSide),
            )
            self._msgbus.publish(topic="okx.order", msg=order)

    def _handle_positions(self, raw: bytes):
        # TODO: update positions from fills
        pass

    def _handle_account(self, raw: bytes):
        # TODO: update account from fills
        pass

    def _handle_fills(self, raw: bytes):
        # TODO: update account from fills
        pass

    def _get_td_mode(self, market: OkxMarket):
        return OkxTdMode.CASH if market.spot else OkxTdMode.CROSS

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

        td_mode = kwargs.pop("td_mode", None)
        if not td_mode:
            td_mode = self._get_td_mode(market)

        params = {
            "inst_id": symbol,
            "td_mode": td_mode.value,
            "side": OkxEnumParser.to_okx_order_side(side).value,
            "ord_type": OkxEnumParser.to_okx_order_type(type, time_in_force).value,
            "sz": str(amount),
        }

        if type == OrderType.LIMIT:
            if not price:
                raise ValueError("Price is required for limit order")
            params["px"] = str(price)
        else:
            if market.spot:
                params["tgtCcy"] = "base_ccy"

        if position_side:
            params["posSide"] = OkxEnumParser.to_okx_position_side(position_side).value
        
        reduce_only = kwargs.pop("reduceOnly", False) or kwargs.pop(
            "reduce_only", False
        )
        if reduce_only:
            params["reduceOnly"] = True

        params.update(kwargs)

        try:
            res = await self._api_client.post_api_v5_trade_order(**params)
            res = res.data[0]
            order = Order(
                exchange=self._exchange_id,
                id=res.ordId,
                client_order_id=res.clOrdId,
                timestamp=int(res.ts),
                symbol=market.symbol,
                type=type,
                side=side,
                amount=amount,
                price=float(price) if price else None,
                time_in_force=time_in_force,
                position_side=position_side,
                status=OrderStatus.PENDING,
                filled=Decimal(0),
                remaining=amount,
            )
            return order
        except Exception as e:
            self._log.error(f"Error creating order: {e} params: {str(params)}")
            order = Order(
                exchange=self._exchange_id,
                timestamp=self._clock.timestamp_ms(),
                symbol=market.symbol,
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

    async def cancel_order(self, symbol: str, order_id: str, **kwargs):
        if self._limiter:
            await self._limiter.acquire()

        market = self._market.get(symbol)
        if not market:
            raise ValueError(f"Symbol {symbol} formated wrongly, or not supported")
        symbol = market.id

        params = {"instId": symbol, "ordId": order_id, **kwargs}

        try:
            res = await self._api_client.post_api_v5_trade_cancel_order(**params)
            res = res.data[0]
            order = Order(
                exchange=self._exchange_id,
                id=res.ordId,
                client_order_id=res.clOrdId,
                timestamp=int(res.ts),
                symbol=symbol,
                status=OrderStatus.CANCELING,
            )
            return order
        except Exception as e:
            self._log.error(f"Error canceling order: {e} params: {str(params)}")
            order = Order(
                exchange=self._exchange_id,
                timestamp=self._clock.timestamp_ms(),
                symbol=symbol,
                status=OrderStatus.CANCEL_FAILED,
            )
            return order

    async def disconnect(self):
        await super().disconnect()
        await self._api_client.close_session()
