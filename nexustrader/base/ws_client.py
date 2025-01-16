import asyncio
import orjson
from abc import ABC, abstractmethod
from typing import Any
from typing import Callable, Literal


from aiolimiter import AsyncLimiter
from nexustrader.core.log import SpdLog
from nexustrader.core.entity import TaskManager
from picows import (
    ws_connect,
    WSFrame,
    WSTransport,
    WSListener,
    WSMsgType,
    WSAutoPingStrategy,
)
from nexustrader.core.nautilius_core import LiveClock

class Listener(WSListener):
    """WebSocket listener implementation that handles connection events and message frames.
    
    Inherits from picows.WSListener to provide WebSocket event handling functionality.
    """
    
    def __init__(self, logger, specific_ping_msg=None, *args, **kwargs):
        """Initialize the WebSocket listener.
        
        Args:
            logger: Logger instance for logging events
            specific_ping_msg: Optional custom ping message
        """
        super().__init__(*args, **kwargs)
        self._log = logger
        self.msg_queue = asyncio.Queue()
        self._specific_ping_msg = specific_ping_msg

    def send_user_specific_ping(self, transport: WSTransport) -> None:
        """Send a custom ping message or default ping frame.
        
        Args:
            transport (picows.WSTransport): WebSocket transport instance
        """
        if self._specific_ping_msg:
            transport.send(WSMsgType.TEXT, self._specific_ping_msg)
            self._log.debug(f"Sent user specific ping {self._specific_ping_msg}")
        else:
            transport.send_ping()
            self._log.debug("Sent default ping.")

    def on_ws_connected(self, transport: WSTransport) -> None:
        """Called when WebSocket connection is established.
        
        Args:
            transport (picows.WSTransport): WebSocket transport instance
        """
        self._log.debug("Connected to Websocket...")

    def on_ws_disconnected(self, transport: WSTransport) -> None:
        """Called when WebSocket connection is closed.
        
        Args:
            transport (picows.WSTransport): WebSocket transport instance
        """
        self._log.debug("Disconnected from Websocket.")

    def on_ws_frame(self, transport: WSTransport, frame: WSFrame) -> None:
        """Handle incoming WebSocket frames.
        
        Args:
            transport (picows.WSTransport): WebSocket transport instance
            frame (picows.WSFrame): Received WebSocket frame
        """
        try:
            match frame.msg_type:
                case WSMsgType.PING:
                    # Only send pong if auto_pong is disabled
                    transport.send_pong(frame.get_payload_as_bytes())
                    return
                case WSMsgType.TEXT:
                    # Queue raw bytes for handler to decode
                    self.msg_queue.put_nowait(frame.get_payload_as_bytes())
                    return
                case WSMsgType.CLOSE:
                    close_code = frame.get_close_code()
                    close_msg = frame.get_close_message()
                    self._log.warning(
                        f"Received close frame. Close code: {close_code}, Close message: {close_msg}"
                    )
                    return
        except Exception as e:
            self._log.error(f"Error processing message: {str(e)}")


class WSClient(ABC):
    def __init__(
        self,
        url: str,
        limiter: AsyncLimiter,
        handler: Callable[..., Any],
        task_manager: TaskManager,
        specific_ping_msg: bytes = None,
        reconnect_interval: int = 1,
        ping_idle_timeout: int = 2,
        ping_reply_timeout: int = 1,
        auto_ping_strategy: Literal[
            "ping_when_idle", "ping_periodically"
        ] = "ping_when_idle",
        enable_auto_ping: bool = True,
        enable_auto_pong: bool = False,
    ):
        self._clock = LiveClock()
        self._url = url
        self._specific_ping_msg = specific_ping_msg
        self._reconnect_interval = reconnect_interval
        self._ping_idle_timeout = ping_idle_timeout
        self._ping_reply_timeout = ping_reply_timeout
        self._enable_auto_pong = enable_auto_pong
        self._enable_auto_ping = enable_auto_ping
        self._listener: Listener = None
        self._transport = None
        self._subscriptions = {}
        self._limiter = limiter
        self._callback = handler
        if auto_ping_strategy == "ping_when_idle":
            self._auto_ping_strategy = WSAutoPingStrategy.PING_WHEN_IDLE
        elif auto_ping_strategy == "ping_periodically":
            self._auto_ping_strategy = WSAutoPingStrategy.PING_PERIODICALLY
        self._task_manager = task_manager
        self._log = SpdLog.get_logger(type(self).__name__, level="DEBUG", flush=True)

    @property
    def connected(self):
        return self._transport and self._listener

    async def _connect(self):
        WSListenerFactory = lambda: Listener(self._log, self._specific_ping_msg)  # noqa: E731
        self._transport, self._listener = await ws_connect(
            WSListenerFactory,
            self._url,
            enable_auto_ping=self._enable_auto_ping,
            auto_ping_idle_timeout=self._ping_idle_timeout,
            auto_ping_reply_timeout=self._ping_reply_timeout,
            auto_ping_strategy=self._auto_ping_strategy,
            enable_auto_pong=self._enable_auto_pong,
        )

    async def connect(self):
        if not self.connected:
            await self._connect()
            self._task_manager.create_task(self._msg_handler(self._listener.msg_queue))
            self._task_manager.create_task(self._connection_handler())

    async def _connection_handler(self):
        while True:
            try:
                if not self.connected:
                    await self._connect()
                    self._task_manager.create_task(
                        self._msg_handler(self._listener.msg_queue)
                    )
                    await self._resubscribe()
                await self._transport.wait_disconnected()
            except Exception as e:
                self._log.error(f"Connection error: {e}")
            finally:
                self._log.debug("Websocket reconnecting...")
                self._transport, self._listener = None, None
                await asyncio.sleep(self._reconnect_interval)

    async def _send(self, payload: dict):
        await self._limiter.acquire()
        self._transport.send(WSMsgType.TEXT, orjson.dumps(payload))

    async def _msg_handler(self, queue: asyncio.Queue):
        while True:
            msg = await queue.get()
            self._callback(msg)
            queue.task_done()

    def disconnect(self):
        if self.connected:
            self._transport.disconnect()

    @abstractmethod
    async def _resubscribe(self):
        pass
