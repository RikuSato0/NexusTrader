import asyncio
import ssl
import certifi
import orjson
import warnings
import aiohttp


import ccxt
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from typing import Callable, Literal
from decimal import Decimal


from aiolimiter import AsyncLimiter
from decimal import ROUND_HALF_UP, ROUND_CEILING, ROUND_FLOOR

from tradebot.schema import Order, BaseMarket
from tradebot.constants import ExchangeType
from tradebot.core.log import SpdLog
from tradebot.core.entity import TaskManager, RateLimit
from tradebot.constants import OrderSide, OrderType, TimeInForce, PositionSide
from picows import (
    ws_connect,
    WSFrame,
    WSTransport,
    WSListener,
    WSMsgType,
    WSAutoPingStrategy,
)
from tradebot.core.nautilius_core import LiveClock, MessageBus


class ExchangeManager(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("apiKey", None)
        self.secret = config.get("secret", None)
        self.exchange_id = ExchangeType(config["exchange_id"])
        self.api = self._init_exchange()
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="INFO", flush=True
        )
        self.is_testnet = config.get("sandbox", False)
        self.market: Dict[str, BaseMarket] = {}
        self.market_id: Dict[str, str] = {}

        if not self.api_key or not self.secret:
            warnings.warn(
                "API Key and Secret not provided, So some features related to trading will not work"
            )
        self.load_markets()

    def _init_exchange(self) -> ccxt.Exchange:
        try:
            exchange_class = getattr(ccxt, self.config["exchange_id"])
        except AttributeError:
            raise AttributeError(
                f"Exchange {self.config['exchange_id']} is not supported"
            )

        api = exchange_class(self.config)
        api.set_sandbox_mode(
            self.config.get("sandbox", False)
        )  # Set sandbox mode if demo trade is enabled
        return api

    @abstractmethod
    def load_markets(self):
        pass
    
    @property
    def linear(self):
        symbols = []
        for symbol, market in self.market.items():
            if market.linear and market.active and not market.future:
                symbols.append(symbol)
        return symbols
    
    @property
    def inverse(self):
        symbols = []
        for symbol, market in self.market.items():
            if market.inverse and market.active and not market.future:
                symbols.append(symbol)
        return symbols
    
    @property
    def spot(self):
        symbols = []
        for symbol, market in self.market.items():
            if market.spot and market.active:
                symbols.append(symbol)
        return symbols
    
    @property
    def future(self):
        symbols = []
        for symbol, market in self.market.items():
            if market.future and market.active:
                symbols.append(symbol)
        return symbols
    
    def amount_to_precision(
        self,
        symbol: str,
        amount: float,
        mode: Literal["round", "ceil", "floor"] = "round",
    ) -> Decimal:
        market = self.market[symbol]
        amount: Decimal = Decimal(str(amount))
        precision = market.precision.amount
        
        if precision >= 1:
            exp = Decimal(int(precision))
            precision_decimal = Decimal('1')  
        else:
            exp = Decimal('1')
            precision_decimal = Decimal(str(precision))
        
        if mode == 'round':
            amount = (amount / exp).quantize(precision_decimal, rounding=ROUND_HALF_UP) * exp
        elif mode == 'ceil':
            amount = (amount / exp).quantize(precision_decimal, rounding=ROUND_CEILING) * exp
        elif mode == 'floor':
            amount = (amount / exp).quantize(precision_decimal, rounding=ROUND_FLOOR) * exp
    
        return amount

    def price_to_precision(
        self,
        symbol: str,
        price: float,
        mode: Literal["round", "ceil", "floor"] = "round",
    ) -> Decimal:
        market = self.market[symbol]
        price: Decimal = Decimal(str(price))

        decimal = market.precision.price
        
        if decimal >= 1:
            exp = Decimal(int(decimal))
            precision_decimal = Decimal('1')  
        else:
            exp = Decimal('1')
            precision_decimal = Decimal(str(decimal))
        
        if mode == 'round':
            price = (price / exp).quantize(precision_decimal, rounding=ROUND_HALF_UP) * exp
        elif mode == 'ceil':
            price = (price / exp).quantize(precision_decimal, rounding=ROUND_CEILING) * exp
        elif mode == 'floor':
            price = (price / exp).quantize(precision_decimal, rounding=ROUND_FLOOR) * exp

        return price



class Listener(WSListener):
    def __init__(self, logger, specific_ping_msg=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._log = logger
        self.msg_queue = asyncio.Queue()
        self._specific_ping_msg = specific_ping_msg

    def send_user_specific_ping(self, transport: WSTransport):
        if self._specific_ping_msg:
            transport.send(WSMsgType.TEXT, self._specific_ping_msg)
            self._log.debug(f"Sent user specific ping {self._specific_ping_msg}")
        else:
            transport.send_ping()
            self._log.debug("Sent default ping.")

    def on_ws_connected(self, transport: WSTransport):
        self._log.debug("Connected to Websocket...")

    def on_ws_disconnected(self, transport: WSTransport):
        self._log.debug("Disconnected from Websocket.")

    def on_ws_frame(self, transport: WSTransport, frame: WSFrame):
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
        self._listener = None
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
            # TODO: handle different event types of messages
            self._callback(msg)
            queue.task_done()

    def disconnect(self):
        if self.connected:
            self._transport.disconnect()

    @abstractmethod
    async def _resubscribe(self):
        pass

class ApiClient(ABC):
    def __init__(
        self,
        api_key: str = None,
        secret: str = None,
        timeout: int = 10,
    ):
        self._api_key = api_key
        self._secret = secret
        self._timeout = timeout
        self._log = SpdLog.get_logger(type(self).__name__, level="INFO", flush=True)
        self._ssl_context = ssl.create_default_context(cafile=certifi.where())
        self._session: Optional[aiohttp.ClientSession] = None
        self._clock = LiveClock()
        
    async def _init_session(self):
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            tcp_connector = aiohttp.TCPConnector(
                ssl=self._ssl_context, enable_cleanup_closed=True
            )
            self._session = aiohttp.ClientSession(
                connector=tcp_connector, json_serialize=orjson.dumps, timeout=timeout
            )

    async def close_session(self):
        if self._session:
            await self._session.close()
            self._session = None

    @abstractmethod
    def raise_error(self, raw: bytes, status: int, headers: Dict[str, Any]):
        raise NotImplementedError("Subclasses must implement this method.")





class PublicConnector(ABC):
    def __init__(
        self,
        account_type,
        market: Dict[str, BaseMarket],
        market_id: Dict[str, str],
        exchange_id: ExchangeType,
        ws_client: WSClient,
        msgbus: MessageBus,
    ):
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )
        self._account_type = account_type
        self._market = market
        self._market_id = market_id
        self._exchange_id = exchange_id
        self._ws_client = ws_client
        self._msgbus = msgbus
        self._clock = LiveClock()
        
    @property
    def account_type(self):
        return self._account_type

    @abstractmethod
    async def subscribe_trade(self, symbol: str):
        pass

    @abstractmethod
    async def subscribe_bookl1(self, symbol: str):
        pass

    @abstractmethod
    async def subscribe_kline(self, symbol: str, interval: str):
        pass

    async def disconnect(self):
        self._ws_client.disconnect() # not needed to await


class PrivateConnector(ABC):
    def __init__(
        self,
        account_type,
        market: Dict[str, BaseMarket],
        market_id: Dict[str, str],
        exchange_id: ExchangeType,
        ws_client: WSClient,
        api_client: ApiClient,
        msgbus: MessageBus,
        rate_limit: RateLimit | None = None,
    ):
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )
        self._account_type = account_type
        self._market = market
        self._market_id = market_id
        self._exchange_id = exchange_id
        self._ws_client = ws_client
        self._api_client = api_client
        self._clock = LiveClock()
        self._msgbus: MessageBus = msgbus
        
        if rate_limit:
            self._limiter = AsyncLimiter(rate_limit.max_rate, rate_limit.time_period)
        else:
            self._limiter = None
        
        
    @property
    def account_type(self):
        return self._account_type

    @abstractmethod
    async def create_order(
        self,
        symbol: str,
        side: OrderSide,
        type: OrderType,
        amount: Decimal,
        price: Decimal,
        time_in_force: TimeInForce,
        position_side: PositionSide,
        **kwargs,
    ) -> Order:
        pass

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str, **kwargs) -> Order:
        pass
    
    @abstractmethod
    async def connect(self):
        pass

    async def disconnect(self):
        self._ws_client.disconnect()
        await self._api_client.close_session()






