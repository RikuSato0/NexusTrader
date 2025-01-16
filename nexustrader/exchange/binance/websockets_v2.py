import asyncio
import orjson

from typing import Literal, Callable
from typing import Any, List
from asynciolimiter import Limiter

from nexustrader.core.log import SpdLog
from nexustrader.exchange.binance.constants import BinanceAccountType
from nexustrader.core.nautilius_core import (
    LiveClock,
    WebSocketClient,
    WebSocketClientError,
    WebSocketConfig,
)


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
        self._log.info("Reconnecting...")
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
            self._log.info(f"Subscribed to {params}")

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
