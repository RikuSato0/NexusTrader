from typing import Dict, Any
from tradebot.exchange.okx import OkxAccountType
from tradebot.exchange.okx.websockets import OkxWSClient
from tradebot.types import Trade, BookL1
from tradebot.constants import EventType
from tradebot.entity import EventSystem


class OkxPublicConnector:
    def __init__(
        self,
        account_type: OkxAccountType,
        market: Dict[str, Any],
        market_id: Dict[str, Any],
    ):
        self._exchange_id = "okx"
        self._market = market
        self._market_id = market_id
        self._ws_client = OkxWSClient(
            account_type=account_type,
            handler=self._ws_msg_handler,
        )

    async def subscribe_trade(self, symbol: str):
        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol
        await self._ws_client.subscribe_trade(symbol)

    async def subscribe_book_l1(self, symbol: str):
        market = self._market.get(symbol, None)
        symbol = market["id"] if market else symbol
        await self._ws_client.subscribe_book_l1(symbol)

    def _ws_msg_handler(self, msg):
        if "event" in msg:
            if msg["event"] == "error":
                # self._log.error(str(msg))
                pass
            elif msg["event"] == "subscribe":
                pass
            elif msg["event"] == "login":
                # self._log.info(f"Login successful: {msg}")
                pass
            elif msg["event"] == "channel-conn-count":
                # self._log.info(f"Channel connection count: {msg['connCount']}")
                pass
        elif "arg" in msg:
            channel = msg["arg"]["channel"]
            match channel:
                case "bbo-tbt":
                    self._parse_bbo_tbt(msg)
                case "trades":
                    self._parse_trade(msg)

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

    def disconnect(self):
        self._ws_client.disconnect()


class OkxPrivateConnector:
    pass
