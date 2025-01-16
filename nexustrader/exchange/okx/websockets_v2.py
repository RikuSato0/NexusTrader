import asyncio
from typing import Callable, Any, Optional
from nautilus_trader.common.component import LiveClock
from nautilus_trader.adapters.okx.websocket.client import OKXWebsocketClient
from nautilus_trader.adapters.okx.common.enums import OKXWsBaseUrlType, OKXBarSize
from nexustrader.exchange.okx import OkxAccountType


class OkxWSClient:
    """OKX WebSocket client manager with business logic."""

    def __init__(
        self,
        handler: Callable[..., Any],
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        is_demo: bool = False,
        account_type: Optional[OkxAccountType] = None,  # compatible with old connector
    ):
        self._clock = LiveClock()
        self._loop = asyncio.get_event_loop()
        self._handler = handler
        self._api_key = api_key
        self._api_secret = api_secret
        self._passphrase = passphrase
        self._is_demo = is_demo
        self._reconnection_count = 0

        # 初始化公共客户端
        self._public_client = self._create_client(OKXWsBaseUrlType.PUBLIC)

        # 只有在提供了完整的API凭证时才创建私有和业务客户端
        self._private_client = None
        self._business_client = None
        if all([api_key, api_secret, passphrase]):
            self._private_client = self._create_client(OKXWsBaseUrlType.PRIVATE)
            self._business_client = self._create_client(OKXWsBaseUrlType.BUSINESS)

    async def _on_reconnect(self) -> None:
        """Handle reconnection events."""
        pass

    @property
    def is_connected(self) -> bool:
        """检查所有相关客户端是否已连接"""
        public_connected = (
            self._public_client
            and hasattr(self._public_client, "_client")
            and self._public_client._client
            and self._public_client._client.is_alive()
        )
        if not self._private_client:
            return public_connected

        private_connected = (
            self._private_client
            and hasattr(self._private_client, "_client")
            and self._private_client._client
            and self._private_client._client.is_alive()
        )
        business_connected = (
            self._business_client
            and hasattr(self._business_client, "_client")
            and self._business_client._client
            and self._business_client._client.is_alive()
        )
        return all([public_connected, private_connected, business_connected])

    async def connect(self) -> None:
        """Connect all available WebSocket clients."""
        if self.is_connected:
            return

        await self._public_client.connect()

        if self._private_client:
            await self._private_client.connect()
        if self._business_client:
            await self._business_client.connect()

    async def disconnect(self) -> None:
        """Disconnect all available WebSocket clients."""
        await self._public_client.disconnect()

        if self._private_client:
            await self._private_client.disconnect()
        if self._business_client:
            await self._business_client.disconnect()

    def _create_client(self, ws_type: OKXWsBaseUrlType) -> OKXWebsocketClient:
        """Create a WebSocket client for specific type."""
        return OKXWebsocketClient(
            clock=self._clock,
            handler=self._handler,
            handler_reconnect=self._on_reconnect,
            api_key=self._api_key if ws_type != OKXWsBaseUrlType.PUBLIC else None,
            api_secret=self._api_secret if ws_type != OKXWsBaseUrlType.PUBLIC else None,
            passphrase=self._passphrase if ws_type != OKXWsBaseUrlType.PUBLIC else None,
            base_url=None,  # Use default URL
            ws_base_url_type=ws_type,
            is_demo=self._is_demo,
            loop=self._loop,
        )

    # Public API methods
    async def subscribe_order_book(self, symbol: str, depth: int = 400) -> None:
        """Subscribe to order book updates."""
        await self.connect()
        await self._public_client.subscribe_order_book(
            instId=symbol,
            depth=depth,
        )

    async def subscribe_trade(self, symbol: str) -> None:
        """Subscribe to trade updates."""
        await self.connect()
        await self._public_client.subscribe_trades(instId=symbol)

    # Business API methods
    # TODO: what is business client?
    async def subscribe_candlesticks(self, symbol: str, interval: str) -> None:
        """Subscribe to candlestick data."""
        await self.connect()
        # Convert interval string to OKXBarSize enum
        bar_size_map = {
            "1m": OKXBarSize.MINUTE_1,
            "3m": OKXBarSize.MINUTE_3,
            "5m": OKXBarSize.MINUTE_5,
            "15m": OKXBarSize.MINUTE_15,
            "30m": OKXBarSize.MINUTE_30,
            "1H": OKXBarSize.HOUR_1,
            "2H": OKXBarSize.HOUR_2,
            "4H": OKXBarSize.HOUR_4,
        }
        bar_size = bar_size_map.get(interval)
        if not bar_size:
            raise ValueError(f"Unsupported interval: {interval}")

        await self._business_client.subscribe_candlesticks(
            instId=symbol,
            bar_size=bar_size,
        )

    # Private API methods
    async def subscribe_account(self) -> None:
        """Subscribe to account updates."""
        await self.connect()
        await self._private_client.subscribe_account()

    async def subscribe_positions(self) -> None:
        """Subscribe to position updates."""
        await self.connect()
        await self._private_client.subscribe_positions()

    async def subscribe_orders(self) -> None:
        """Subscribe to order updates."""
        await self.connect()
        await self._private_client.subscribe_orders()

    async def subscribe_fills(self) -> None:
        """Subscribe to trade fills."""
        await self.connect()
        await self._private_client.subscribe_fills()

    # async def _on_reconnect(self) -> None:
    #     """重连事件处理"""
    #     self.reconnection_count += 1
    #     self.last_reconnect_time = datetime.now()
    #     logger.warning(
    #         f"WebSocket reconnected! Count: {self.reconnection_count}, "
    #         f"Disconnect duration: {self.last_reconnect_time - self.last_disconnect_time}"
    #     )

    # async def simulate_disconnect(self, client_type: str = "public"):
    #     """
    #     模拟断开连接
    #     :param client_type: 'public', 'private', 或 'business'
    #     """
    #     client = getattr(self, f"_{client_type}_client")
    #     if client and hasattr(client, "_client") and client._client:
    #         logger.info(f"Simulating disconnect for {client_type} client...")
    #         self.last_disconnect_time = datetime.now()
    #         await client._client.disconnect()
    #         logger.info(f"{client_type.capitalize()} client disconnected")

    # async def test_reconnection(self, interval: int = 15, times: int = 3):
    #     """
    #     测试重连逻辑
    #     :param interval: 断连间隔(秒)
    #     :param times: 测试次数
    #     """
    #     for i in range(times):
    #         logger.info(f"Starting reconnection test #{i+1}")
    #         await asyncio.sleep(interval)

    #         # 模拟断连
    #         await self.simulate_disconnect("public")
    #         if self._api_key:  # 如果有API key，也测试私有连接
    #             await self.simulate_disconnect("private")
    #             await self.simulate_disconnect("business")

    #         # 等待自动重连
    #         await asyncio.sleep(10)

    #         logger.info(
    #             f"Test #{i+1} completed. "
    #             f"Total reconnections: {self.reconnection_count}"
    #         )
