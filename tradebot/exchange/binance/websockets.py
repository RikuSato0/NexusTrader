import time
import asyncio
import orjson

from typing import Literal, Callable
from typing import Any, List
from asynciolimiter import Limiter

from tradebot.log import SpdLog
from tradebot.base import WSClient
from tradebot.exchange.binance.constants import STREAM_URLS
from tradebot.exchange.binance.constants import BinanceAccountType

from nautilus_trader.common.component import LiveClock
from nautilus_trader.core.nautilus_pyo3 import WebSocketClient
from nautilus_trader.core.nautilus_pyo3 import WebSocketClientError
from nautilus_trader.core.nautilus_pyo3 import WebSocketConfig


class BinanceWSClient(WSClient):
    def __init__(self, account_type: BinanceAccountType, handler: Callable[..., Any]):
        self._account_type = account_type
        url = STREAM_URLS[account_type]
        super().__init__(url, limiter=Limiter(3 / 1), handler=handler)

    async def _subscribe(self, params: str, subscription_id: str):
        if subscription_id not in self._subscriptions:
            await self.connect()
            await self._limiter.wait()
            id = time.time_ns() // 1_000_000
            payload = {
                "method": "SUBSCRIBE",
                "params": [params],
                "id": id,
            }
            self._subscriptions[subscription_id] = payload
            self._send(payload)
            self._log.info(f"Subscribing to {subscription_id}...")
        else:
            self._log.info(f"Already subscribed to {subscription_id}")

    async def subscribe_agg_trade(self, symbol: str):
        if (
            self._account_type.is_isolated_margin_or_margin
            or self._account_type.is_portfolio_margin
        ):
            raise ValueError(
                "Not Supported for `Margin Account` or `Portfolio Margin Account`"
            )
        subscription_id = f"agg_trade.{symbol}"
        params = f"{symbol.lower()}@aggTrade"
        await self._subscribe(params, subscription_id)

    async def subscribe_trade(self, symbol: str):
        if (
            self._account_type.is_isolated_margin_or_margin
            or self._account_type.is_portfolio_margin
        ):
            raise ValueError(
                "Not Supported for `Margin Account` or `Portfolio Margin Account`"
            )
        subscription_id = f"trade.{symbol}"
        params = f"{symbol.lower()}@trade"
        await self._subscribe(params, subscription_id)

    async def subscribe_book_ticker(self, symbol: str):
        if (
            self._account_type.is_isolated_margin_or_margin
            or self._account_type.is_portfolio_margin
        ):
            raise ValueError(
                "Not Supported for `Margin Account` or `Portfolio Margin Account`"
            )
        subscription_id = f"book_ticker.{symbol}"
        params = f"{symbol.lower()}@bookTicker"
        await self._subscribe(params, subscription_id)

    async def subscribe_mark_price(
        self, symbol: str, interval: Literal["1s", "3s"] = "1s"
    ):
        if not self._account_type.is_future:
            raise ValueError("Only Supported for `Future Account`")
        subscription_id = f"mark_price.{symbol}"
        params = f"{symbol.lower()}@markPrice@{interval}"
        await self._subscribe(params, subscription_id)

    async def subscribe_user_data_stream(self, listen_key: str):
        subscription_id = "user_data_stream"
        await self._subscribe(listen_key, subscription_id)

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
        if (
            self._account_type.is_isolated_margin_or_margin
            or self._account_type.is_portfolio_margin
        ):
            raise ValueError(
                "Not Supported for `Margin Account` or `Portfolio Margin Account`"
            )
        subscription_id = f"kline.{symbol}.{interval}"
        params = f"{symbol.lower()}@kline_{interval}"
        await self._subscribe(params, subscription_id)

    async def _resubscribe(self):
        for _, payload in self._subscriptions.items():
            await self._limiter.wait()
            self._send(payload)


####################################################################################################
############################### CODE USING THE NAUTILUS_PY03 LIBRARY ###############################
####################################################################################################


class BinanceWebSocketClient:
    def __init__(
        self,
        account_type: BinanceAccountType,
        handler: Callable[[bytes], None],
        loop: asyncio.AbstractEventLoop,
    ):
        self._url = account_type.ws_url
        self._loop = loop
        self._clock = LiveClock()
        self._client: WebSocketClient = None
        self._handler: Callable[[bytes], None] = handler
        self._subscriptions: List[str] = []
        self._is_connected = False
        self._limiter = Limiter(3 / 1)
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="INFO", flush=True
        )

    def _ping_handler(self, raw: bytes) -> None:
        self._loop.create_task(self._send_pong(raw))

    async def _send_pong(self, raw: bytes) -> None:
        if self._client is None:
            return

        try:
            await self._client.send_pong(raw)
        except WebSocketClientError as e:
            self._log.error(str(e))

    async def connect(self) -> None:
        if self._client is not None or self._is_connected:
            return

        config = WebSocketConfig(
            url=self._url,
            handler=self._handler,
            heartbeat=60,
            headers=[],
            ping_handler=self._ping_handler,
        )

        self._client = await WebSocketClient.connect(
            config=config,
            post_reconnection=self._reconnect,
        )

        self._is_connected = True

    async def disconnect(self) -> None:
        if self._client is None or not self._is_connected:
            return

        self._log.info("Disconnecting...")
        try:
            await self._client.disconnect()
        except WebSocketClientError as e:
            self._log.error(str(e))

        self._is_connected = False
        self._client = None

    async def _subscribe(self, params: str) -> None:
        if params in self._subscriptions:
            self._log.info(f"Cannot subscribe to {params}: Already subscribed")
            return

        self._subscriptions.append(params)

        if self._client is None or not self._is_connected:
            raise RuntimeError(
                "WebSocket client is not connected. Call `connect()` first."
            )

        payload = {
            "method": "SUBSCRIBE",
            "params": [params],
            "id": self._clock.timestamp_ms(),
        }

        await self._send(payload)
        self._log.info(f"Subscribed to {params}")

    async def _reconnect(self) -> None:
        if not self._subscriptions:
            self._log.info("No subscriptions to resubscribe")
            return

        self._loop.create_task(self._subscribe_all())

    async def _subscribe_all(self) -> None:
        if self._client is None or not self._is_connected:
            raise RuntimeError(
                "WebSocket client is not connected. Call `connect()` first."
            )

        for params in self._subscriptions:
            payload = {
                "method": "SUBSCRIBE",
                "params": [params],
                "id": self._clock.timestamp_ms(),
            }
            await self._send(payload)

    async def _send(self, msg: dict[str, Any]) -> None:
        if self._client is None or not self._is_connected:
            raise RuntimeError(
                "WebSocket client is not connected. Call `connect()` first."
            )

        try:
            await self._limiter.wait()
            await self._client.send_text(orjson.dumps(msg))
        except WebSocketClientError as e:
            self._log.error(str(e))

    async def subscribe_agg_trade(self, symbol: str) -> None:
        params = f"{symbol.lower()}@aggTrade"
        await self._subscribe(params)

    async def subscribe_trade(self, symbol: str) -> None:
        params = f"{symbol.lower()}@trade"
        await self._subscribe(params)

    async def subscribe_book_ticker(self, symbol: str) -> None:
        params = f"{symbol.lower()}@bookTicker"
        await self._subscribe(params)

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
    ) -> None:
        params = f"{symbol.lower()}@kline_{interval}"
        await self._subscribe(params)
