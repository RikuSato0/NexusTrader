from tradebot.exchange.okx import OkxAccountType
from tradebot.exchange.okx.websockets import OkxWSClient
from tradebot.exchange.okx.exchange import OkxExchangeManager
from tradebot.types import Trade, BookL1, Kline
from tradebot.constants import EventType
from tradebot.entity import EventSystem
from tradebot.base import PublicConnector


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
            ws_client=OkxWSClient(
                account_type=account_type,
                handler=self._ws_msg_handler,
            ),
        )

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
        if "event" in msg:
            if msg["event"] == "error":
                self._log.error(str(msg))
            elif msg["event"] == "subscribe":
                pass
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


class OkxPrivateConnector:
    pass
