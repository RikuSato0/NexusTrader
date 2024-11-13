from typing import cast
import orjson
from tradebot.exchange.okx import OkxAccountType
from tradebot.exchange.okx.websockets import OkxWSClient
from tradebot.exchange.okx.websockets_v2 import OkxWSClient as OkxWSClientV2
from tradebot.exchange.okx.exchange import OkxExchangeManager
from tradebot.types import Trade, BookL1, Kline
from tradebot.constants import EventType
from tradebot.entity import EventSystem
from tradebot.base import PublicConnector, PrivateConnector
from tradebot.exchange.okx.rest_api import OkxApiClient



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
        self._ws_client = cast(OkxWSClientV2, self._ws_client)

    async def subscribe_trade(self, symbol: str):
        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol
        await self._ws_client.subscribe_trade(symbol)

    async def subscribe_bookl1(self, symbol: str):
        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol
        await self._ws_client.subscribe_order_book(symbol, channel="bbo-tbt")

    async def subscribe_kline(self, symbol: str, interval: str):
        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol
        await self._ws_client.subscribe_candlesticks(symbol, interval)

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
    ):
        super().__init__(
            account_type=account_type,
            market=exchange.market,
            market_id=exchange.market_id,
            exchange_id=exchange.exchange_id,
            ws_client=OkxWSClientV2(
                account_type=account_type,
                handler=self._ws_msg_handler,
                api_key=exchange.api_key,
                secret=exchange.secret,
                passphrase=exchange.passphrase,
            ),
        )
        self._ws_client: OkxWSClient = self._ws_client

        self._api_client = OkxApiClient(
            api_key=exchange.api_key,
            secret=exchange.secret,
            passphrase=exchange.passphrase,
        )

    def _ws_msg_handler(self, msg):
        msg = orjson.loads(msg)
        if "event" in msg:
            if msg["event"] == "error":
                self._log.error(msg.get("msg", "Unknown error"))
            elif msg["event"] == "subscribe":
                self._log.info(f"Subscribed to {msg['arg']['channel']}")
            elif msg["event"] == "login":
                self._log.info("Login success")
            elif msg["event"] == "channel-conn-count":
                self._log.info(
                    f"Channel {msg['channel']} connection count: {msg['connCount']}"
                )
        elif "arg" in msg:
            channel: str = msg["arg"]["channel"]
            if channel == "orders":
                self._parse_orders(msg)
            elif channel == "positions":
                self._parse_positions(msg)
            elif channel == "account":
                self._parse_account(msg)

    def _parse_orders(self, msg):
        """
        {
            'arg': {
                'channel': 'orders', // Channel name
                'instType': 'ANY', // Instrument type
                'uid': '422205842008504732' // User Identifier
            },
            'data': [
                {
                    'instType': 'SPOT', // Instrument type
                    'instId': 'BTC-USDT', // Instrument ID
                    'tgtCcy': '', // Order quantity unit setting for sz. Default is quote_ccy for buy, base_ccy for sell
                    'ccy': '', // Margin currency, only applicable to cross MARGIN orders in Spot and futures mode
                    'ordId': '1848670189392691200', // Order ID
                    'clOrdId': '', // Client Order ID as assigned by the client
                    'tag': '', // Order tag
                    'px': '65465.4', // Price
                    'pxUsd': '', // Options price in USD (only for options)
                    'pxVol': '', // Implied volatility of the options order (only for options)
                    'sz': '3.00708129', // Original order quantity
                    'notionalUsd': '196958.20937210717', // Estimated notional value in USD
                    'ordType': 'limit', // Order type (market, limit, post_only, fok, ioc, etc.)
                    'side': 'sell', // Order side, buy or sell
                    'posSide': '', // Position side, long or short (only for FUTURES/SWAP)
                    'tdMode': 'cross', // Trade mode: cross, isolated, or cash
                    'accFillSz': '0', // Accumulated filled quantity
                    'fillNotionalUsd': '', // Filled notional value in USD of the order
                    'avgPx': '0', // Average filled price
                    'state': 'live', // Order state (canceled, live, partially_filled, filled, mmp_canceled)
                    'lever': '5', // Leverage (only for MARGIN/FUTURES/SWAP)
                    'attachAlgoClOrdId': '', // Client-supplied Algo ID for TP/SL orders
                    'tpTriggerPx': '', // Take-profit trigger price
                    'tpTriggerPxType': '', // Take-profit trigger price type (last, index, mark)
                    'tpOrdPx': '', // Take-profit order price
                    'slTriggerPx': '', // Stop-loss trigger price
                    'slTriggerPxType': '', // Stop-loss trigger price type (last, index, mark)
                    'slOrdPx': '', // Stop-loss order price
                    'stpId': '', // Self trade prevention ID (deprecated)
                    'stpMode': 'cancel_maker', // Self trade prevention mode
                    'feeCcy': 'USDT', // Fee currency
                    'fee': '0', // Fee and rebate
                    'rebateCcy': 'BTC', // Rebate currency
                    'rebate': '0', // Rebate amount
                    'pnl': '0', // Profit and loss
                    'source': '', // Order source
                    'cancelSource': '', // Source of order cancellation
                    'category': 'normal', // Order category
                    'uTime': '1727597064972', // Update time (Unix timestamp in milliseconds)
                    'cTime': '1727597064972', // Creation time (Unix timestamp in milliseconds)
                    'reqId': '', // Client Request ID for order amendment
                    'amendResult': '', // Result of amending the order
                    'reduceOnly': 'false', // Whether the order can only reduce position size
                    'quickMgnType': '', // Quick Margin type (only for Quick Margin Mode of isolated margin)
                    'algoClOrdId': '', // Client-supplied Algo ID for triggered algo orders
                    'algoId': '', // Algo ID for triggered algo orders
                    'code': '0', // Error code (0 is default)
                    'msg': '', // Error message (empty string is default)
                    // Additional fields omitted for brevity
                }
            ]
        }

        {
            'arg': {
                'channel': 'orders', // Channel name
                'instType': 'ANY', // Instrument type
                'uid': '422205842008504732' // User ID
            },
            'data': [{
                'instType': 'SPOT', // Instrument type
                'instId': 'BTC-USDT', // Instrument ID
                'tgtCcy': '', // Target currency
                'ccy': '', // Margin currency
                'ordId': '1848670189392691200', // Order ID
                'clOrdId': '', // Client order ID
                'algoClOrdId': '', // Algo client order ID
                'algoId': '', // Algo ID
                'tag': '', // Order tag
                'px': '65465.4', // Price
                'sz': '3.00708129', // Order size
                'notionalUsd': '196964.11516549162', // Notional value in USD
                'ordType': 'limit', // Order type
                'side': 'sell', // Order side
                'posSide': '', // Position side
                'tdMode': 'cross', // Trade mode
                'accFillSz': '2.11969899', // Accumulated filled size
                'fillNotionalUsd': '138840.48873934377', // Filled notional in USD
                'avgPx': '65465.4', // Average filled price
                'state': 'partially_filled', // Order state
                'lever': '5', // Leverage
                'pnl': '0', // Profit and loss
                'feeCcy': 'USDT', // Fee currency
                'fee': '-111.0135538079568', // Fee amount
                'rebateCcy': 'BTC', // Rebate currency
                'rebate': '0', // Rebate amount
                'category': 'normal', // Order category
                'uTime': '1727597075013', // Update time
                'cTime': '1727597064972', // Creation time
                'source': '', // Order source
                'reduceOnly': 'false', // Reduce only flag
                'cancelSource': '', // Cancel source
                'quickMgnType': '', // Quick margin type
                'stpId': '', // STP ID
                'stpMode': 'cancel_maker', // STP mode
                'attachAlgoClOrdId': '', // Attached algo client order ID
                'lastPx': '65465.4', // Last filled price
                'isTpLimit': 'false', // Take profit limit flag
                'slTriggerPx': '', // Stop loss trigger price
                'slTriggerPxType': '', // Stop loss trigger price type
                'tpOrdPx': '', // Take profit order price
                'tpTriggerPx': '', // Take profit trigger price
                'tpTriggerPxType': '', // Take profit trigger price type
                'slOrdPx': '', // Stop loss order price
                'fillPx': '65465.4', // Fill price
                'tradeId': '797592328', // Trade ID
                'fillSz': '0.02', // Fill size
                'fillTime': '1727597075013', // Fill timestamp
                'fillPnl': '0', // Fill PNL
                'fillFee': '-1.0474464', // Fill fee
                'fillFeeCcy': 'USDT', // Fill fee currency
                'execType': 'M', // Execution type
                'fillPxVol': '', // Fill price volatility
                'fillPxUsd': '', // Fill price in USD
                'fillMarkVol': '', // Fill mark volatility
                'fillFwdPx': '', // Fill forward price
                'fillMarkPx': '', // Fill mark price
                'amendSource': '', // Amendment source
                'reqId': '', // Request ID
                'amendResult': '', // Amendment result
                'code': '0', // Error code
                'msg': '', // Error message
                'pxType': '', // Price type
                'pxUsd': '', // Price in USD
                'pxVol': '', // Price volatility
                'linkedAlgoOrd': {'algoId': ''}, // Linked algo order
                'attachAlgoOrds': [] // Attached algo orders
            }]
        }
        """
        id = msg["data"][0]["instId"]
        market = self._market_id[id]

    def _parse_positions(self, msg):
        pass

    def _parse_account(self, msg):
        pass

    async def connect(self):
        await super().connect()
        await self._ws_client.subscribe_orders()
        await self._ws_client.subscribe_positions()
        await self._ws_client.subscribe_account()
