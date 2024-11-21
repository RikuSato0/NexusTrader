from typing import cast
import orjson
import msgspec
from decimal import Decimal
from tradebot.exchange.okx import OkxAccountType
from tradebot.entity import AsyncCache
from tradebot.exchange.okx.websockets import OkxWSClient
from tradebot.exchange.okx.websockets_v2 import OkxWSClient as OkxWSClientV2
from tradebot.exchange.okx.exchange import OkxExchangeManager
from tradebot.types import Trade, BookL1, Kline
from tradebot.exchange.okx.types import OkxMarket
from tradebot.constants import (
    EventType,
    OrderStatus,
    OrderType,
    TimeInForce,
    PositionSide,
)
from tradebot.entity import EventSystem
from tradebot.base import PublicConnector, PrivateConnector, OrderManagerSystem
from tradebot.exchange.okx.rest_api import OkxApiClient
from tradebot.types import Order, OrderSide, OrderType
from tradebot.exchange.okx.constants import (
    OKXWsGeneralMsg,
    OKXWsEventMsg,
    OKXWsPushDataMsg,
    OKXWsAccountPushDataMsg,
    OKXWsFillsPushDataMsg,
    OKXWsOrdersPushDataMsg,
    OKXWsPositionsPushDataMsg,
    TdMode,
    OkxEnumParser,
    OkxOrderType,
)


class OkxPublicConnector(PublicConnector):
    def __init__(
        self,
        account_type: OkxAccountType,
        exchange: OkxExchangeManager,
    ):
        super().__init__(
            account_type=account_type,
            market=exchange.market,
            market_id=exchange.market_id,
            exchange_id=exchange.exchange_id,
            ws_client=OkxWSClientV2(
                account_type=account_type,
                handler=self._ws_msg_handler,
            ),
        )
        self.ws_client = cast(OkxWSClientV2, self.ws_client)

    async def subscribe_trade(self, symbol: str):
        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol
        await self.ws_client.subscribe_trade(symbol)

    async def subscribe_bookl1(self, symbol: str):
        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol
        await self.ws_client.subscribe_order_book(symbol, channel="bbo-tbt")

    async def subscribe_kline(self, symbol: str, interval: str):
        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol
        await self.ws_client.subscribe_candlesticks(symbol, interval)

    def _ws_msg_handler(self, msg):
        msg = orjson.loads(msg)
        if "event" in msg:
            if msg["event"] == "error":
                self._log.error(str(msg))
            elif msg["event"] == "subscribe":
                self._log.info(
                    f"Subscribed to {msg['arg']['channel']}.{msg['arg']['instId']}"
                )
        elif "arg" in msg:
            channel: str = msg["arg"]["channel"]
            if channel == "bbo-tbt":
                self._parse_bbo_tbt(msg)
            elif channel == "trades":
                self._parse_trade(msg)
            elif channel.startswith("candle"):
                self._parse_kline(msg)

    def _parse_kline(self, msg):
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
        data = msg["data"][0]
        id = msg["arg"]["instId"]
        market = self._market_id[id]

        kline = Kline(
            exchange=self._exchange_id,
            symbol=market["symbol"],
            interval=msg["arg"]["channel"],
            open=float(data[1]),
            high=float(data[2]),
            low=float(data[3]),
            close=float(data[4]),
            volume=float(data[5]),
            timestamp=int(data[0]),
        )

        EventSystem.emit(EventType.KLINE, kline)

    def _parse_trade(self, msg):
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
        data = msg["data"][0]
        id = msg["arg"]["instId"]
        market = self._market_id[id]

        trade = Trade(
            exchange=self._exchange_id,
            symbol=market["symbol"],
            price=float(data["px"]),
            size=float(data["sz"]),
            timestamp=int(data["ts"]),
        )
        EventSystem.emit(EventType.TRADE, trade)

    def _parse_bbo_tbt(self, msg):
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
        data = msg["data"][0]
        id = msg["arg"]["instId"]
        market = self._market_id[id]

        bookl1 = BookL1(
            exchange=self._exchange_id,
            symbol=market["symbol"],
            bid=float(data["bids"][0][0]),
            ask=float(data["asks"][0][0]),
            bid_size=float(data["bids"][0][1]),
            ask_size=float(data["asks"][0][1]),
            timestamp=int(data["ts"]),
        )
        EventSystem.emit(EventType.BOOKL1, bookl1)


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
        self._oms = OrderManagerSystem(
            cache=self._cache,
        )

        self._decoder_ws_general_msg = msgspec.json.Decoder(OKXWsGeneralMsg)
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
