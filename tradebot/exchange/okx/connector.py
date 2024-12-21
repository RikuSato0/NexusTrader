import orjson
import msgspec
from decimal import Decimal
from tradebot.exchange.okx import OkxAccountType
from tradebot.core.cache import AsyncCache
from tradebot.exchange.okx.websockets import OkxWSClient
from tradebot.exchange.okx.exchange import OkxExchangeManager
from tradebot.exchange.okx.schema import OkxWsGeneralMsg
from tradebot.schema import Trade, BookL1, Kline, Order
from tradebot.exchange.okx.schema import OkxMarket, OkxWsBboTbtMsg, OkxWsCandleMsg, OkxWsTradeMsg
from tradebot.constants import (
    OrderStatus,
    TimeInForce,
    PositionSide,
)
from tradebot.base import PublicConnector, PrivateConnector
from tradebot.base import OrderManagementSystem
from tradebot.core.nautilius_core import MessageBus
from tradebot.core.entity import TaskManager
from tradebot.exchange.okx.rest_api import OkxApiClient
from tradebot.constants import OrderSide, OrderType
from tradebot.exchange.okx.constants import (
    OKXWsEventMsg,
    OKXWsPushDataMsg,
    OKXWsAccountPushDataMsg,
    OKXWsFillsPushDataMsg,
    OKXWsOrdersPushDataMsg,
    OKXWsPositionsPushDataMsg,
    TdMode,
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
        try:
            if raw == b"pong":
                self._ws_client._transport.notify_user_specific_pong_received()
                self._log.debug(f"Pong received:{str(raw)}")
                return
            ws_msg: OkxWsGeneralMsg = self._ws_msg_general_decoder.decode(raw)
            if ws_msg.is_event_msg:
                return
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
        data = msg.data[0]
        id = msg.arg.instId
        symbol = self._market_id[id]

        kline = Kline(
            exchange=self._exchange_id,
            symbol=symbol,
            interval=msg.arg.channel,
            open=float(data[1]),
            high=float(data[2]),
            low=float(data[3]),
            close=float(data[4]),
            volume=float(data[5]),
            timestamp=int(data[0]),
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
    def __init__(
        self,
        account_type: OkxAccountType,
        exchange: OkxExchangeManager,
        strategy_id: str = None,
        user_id: str = None,
    ):
        super().__init__(
            account_type=account_type,
            market=exchange.market,
            market_id=exchange.market_id,
            exchange_id=exchange.exchange_id,
            ws_client=OkxWSClient(
                account_type=account_type,
                handler=self._ws_msg_handler,
                api_key=exchange.api_key,
                secret=exchange.secret,
                passphrase=exchange.passphrase,
            ),
            cache=AsyncCache(
                account_type="OKX",
                strategy_id=strategy_id,
                user_id=user_id,
            ),
        )

        self._api_client = OkxApiClient(
            api_key=exchange.api_key,
            secret=exchange.secret,
            passphrase=exchange.passphrase,
            account_type=account_type,
        )
        self._oms = OrderManagementSystem(
            cache=self._cache,
        )

        self._decoder_ws_general_msg = msgspec.json.Decoder(OkxWsGeneralMsg)
        self._decoder_ws_event_msg = msgspec.json.Decoder(OKXWsEventMsg)
        self._decoder_ws_push_data_msg = msgspec.json.Decoder(OKXWsPushDataMsg)
        self._decoder_ws_orders_msg = msgspec.json.Decoder(OKXWsOrdersPushDataMsg)
        self._decoder_ws_account_msg = msgspec.json.Decoder(OKXWsAccountPushDataMsg)
        self._decoder_ws_fills_msg = msgspec.json.Decoder(OKXWsFillsPushDataMsg)
        self._decoder_ws_positions_msg = msgspec.json.Decoder(OKXWsPositionsPushDataMsg)

    @property
    def ws_client(self) -> OkxWSClient:
        return self._ws_client

    def _ws_msg_handler(self, raw: bytes):
        msg = self._decoder_ws_general_msg.decode(raw)

        if msg.is_event_msg:
            msg = self._decoder_ws_event_msg.decode(raw)
            if msg.event == "error":
                self._log.error(msg)
            elif msg.event == "login":
                self._log.info("Login success")
            elif msg.event == "subscribe":
                self._log.info(f"Subscribed to {msg.arg.channel}")
            elif msg.event == "channel-conn-count":
                self._log.info(
                    f"Channel {msg.channel} connection count: {msg.connCount}"
                )

        elif msg.is_push_data_msg:
            push_data = self._decoder_ws_push_data_msg.decode(raw)
            channel = push_data.arg.channel
            if channel == "account":
                self._parse_account(raw)
            elif channel == "fills":
                self._parse_fills(raw)
            elif channel == "orders":
                self._parse_orders(raw)
            elif channel == "positions":
                self._parse_positions(raw)

    def _parse_orders(self, raw: bytes):
        orders_push_data: OKXWsOrdersPushDataMsg = self._decoder_ws_orders_msg.decode(
            raw
        )
        print(orjson.loads(raw))
        # print(orders_push_data.data)
        # self._log.info(str(orders_push_data.data))
        return orders_push_data.data

    def _parse_positions(self, raw: bytes):
        """nautilus updates positions from fills."""
        positions_push_data: OKXWsPositionsPushDataMsg = (
            self._decoder_ws_positions_msg.decode(raw)
        )
        print(orjson.loads(raw))
        # print(positions_push_data.data)
        # self._log.info(str(positions_push_data.data))
        return positions_push_data.data

    def _parse_account(self, raw: bytes):
        account_push_data: OKXWsAccountPushDataMsg = (
            self._decoder_ws_account_msg.decode(raw)
        )
        print(orjson.loads(raw))
        # print(account_push_data.data)
        # self._log.info(str(account_push_data.data))
        return account_push_data.data

    def _parse_fills(self, raw: bytes):
        fills_push_data: OKXWsFillsPushDataMsg = self._decoder_ws_fills_msg.decode(raw)
        # TODO
        return fills_push_data.data

    async def connect(self):
        await super().connect()
        await self.ws_client.subscribe_orders()
        await self.ws_client.subscribe_positions()
        # await self.ws_client.subscrbe_fills()  # vip5 or above only
        await self.ws_client.subscribe_account()

    def _get_td_mode(self, market: OkxMarket):
        return TdMode.CASH if market.spot else TdMode.CROSS  # ?

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
        market = self._market.get(symbol)
        if not market:
            raise ValueError(f"Symbol {symbol} formated wrongly, or not supported")
        symbol = market.id

        params = {
            "instId": symbol,
            "tdMode": self._get_td_mode(market).value,
            "side": OkxEnumParser.to_okx_order_side(side).value,
            "ordType": OkxEnumParser.to_okx_order_type(type, time_in_force).value,
            "sz": str(amount),
        }

        if type == OrderType.LIMIT:
            if not price:
                raise ValueError("Price is required for limit order")
            params["px"] = str(price)

        if position_side:
            params["posSide"] = OkxEnumParser.to_okx_position_side(position_side).value

        params.update(kwargs)

        try:
            _res = await self._api_client.post_v5_order_create(**params)
            res = _res.data[0]
            order = Order(
                exchange=self._exchange_id,
                id=res.ordId,
                client_order_id=res.clOrdId,
                timestamp=int(res.ts),
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

    async def cancel_order(self, symbol: str, order_id: str, **kwargs):
        market = self._market.get(symbol)
        if not market:
            raise ValueError(f"Symbol {symbol} formated wrongly, or not supported")
        exchange_symbol = market.id

        params = {"instId": exchange_symbol, "ordId": order_id, **kwargs}

        try:
            _res = await self._api_client.post_v5_order_cancel(**params)
            res = _res.data[0]
            order = Order(
                exchange=self._exchange_id,
                id=res.ordId,
                client_order_id=res.clOrdId,
                timestamp=int(res.ts),
                symbol=symbol,
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

    async def disconnect(self):
        await super().disconnect()
        await self._api_client.close_session()
