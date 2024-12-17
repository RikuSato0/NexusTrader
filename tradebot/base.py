import asyncio
import time
import ssl
import certifi
import orjson
import warnings
import aiohttp

# import ccxt.pro as ccxtpro
import ccxt
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from typing import Callable, Literal
from collections import defaultdict
from decimal import Decimal


from asynciolimiter import Limiter
from ccxt.base.errors import RequestTimeout
from aiohttp.client_exceptions import ClientResponseError, ClientError
from decimal import ROUND_HALF_UP, ROUND_CEILING, ROUND_FLOOR


from tradebot.log import SpdLog
from tradebot.entity import EventSystem, TaskManager
from tradebot.constants import OrderStatus
from tradebot.types import Order, BaseMarket
from tradebot.entity import AsyncCache
from tradebot.exceptions import OrderError, ExchangeResponseError
from tradebot.constants import OrderSide, OrderType, TimeInForce, PositionSide
from picows import (
    ws_connect,
    WSFrame,
    WSTransport,
    WSListener,
    WSMsgType,
    WSAutoPingStrategy,
)
from tradebot.core.nautilius_core import LiveClock


class ExchangeManager(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("apiKey", None)
        self.secret = config.get("secret", None)
        self.exchange_id = config.get("exchange_id", None)
        self.api = self._init_exchange()
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="INFO", flush=True
        )
        self.is_testnet = config.get("sandbox", False)
        self.market: Dict[str, BaseMarket] = {}
        self.market_id: Dict[str, BaseMarket] = {}

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
        

    # __del__ will call .close() method
    # async def close(self):
    #     await self.api.close()


class AccountManager(ABC):
    pass


class OrderManager(ABC):
    def __init__(self, exchange: ExchangeManager):
        self._exchange = exchange
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="INFO", flush=True
        )

    @abstractmethod
    async def handle_request_timeout(
        self, method: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass

    async def place_limit_order(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        amount: Decimal,
        price: Decimal,
        handle_timeout: bool = True,
        **params,
    ) -> Dict[str, Any]:
        try:
            res = await self._exchange.api.create_order(
                symbol=symbol,
                type="limit",
                side=side,
                amount=amount,
                price=price,
                params=params,
            )
            return res
        except RequestTimeout:
            if handle_timeout:
                return await self.handle_request_timeout(
                    "place_limit_order",
                    {
                        "symbol": symbol,
                        "side": side,
                        "amount": amount,
                        "price": price,
                        **params,
                    },
                )
            else:
                return OrderError(
                    "Request Timeout",
                    {
                        "symbol": symbol,
                        "side": side,
                        "amount": amount,
                        "price": price,
                        **params,
                    },
                )
        except Exception as e:
            return OrderError(
                e,
                {
                    "symbol": symbol,
                    "side": side,
                    "amount": amount,
                    "price": price,
                    **params,
                },
            )

    async def place_limit_order_ws(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        amount: Decimal,
        price: Decimal,
        handle_timeout: bool = True,
        **params,
    ) -> Dict[str, Any]:
        try:
            res = await self._exchange.api.create_order_ws(
                symbol=symbol,
                type="limit",
                side=side,
                amount=amount,
                price=price,
                params=params,
            )
            return res
        except RequestTimeout:
            if handle_timeout:
                return await self.handle_request_timeout(
                    "place_limit_order_ws",
                    {
                        "symbol": symbol,
                        "side": side,
                        "amount": amount,
                        "price": price,
                        **params,
                    },
                )
            else:
                return OrderError(
                    "Request Timeout",
                    {
                        "symbol": symbol,
                        "side": side,
                        "amount": amount,
                        "price": price,
                        **params,
                    },
                )
        except Exception as e:
            return OrderError(
                e,
                {
                    "symbol": symbol,
                    "side": side,
                    "amount": amount,
                    "price": price,
                    **params,
                },
            )

    async def place_market_order(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        amount: Decimal,
        handle_timeout: bool = True,
        **params,
    ) -> Dict[str, Any]:
        try:
            res = await self._exchange.api.create_order(
                symbol=symbol,
                type="market",
                side=side,
                amount=amount,
                params=params,
            )
            return res
        except RequestTimeout:
            if handle_timeout:
                return await self.handle_request_timeout(
                    "place_market_order",
                    {
                        "symbol": symbol,
                        "side": side,
                        "amount": amount,
                        "price": None,
                        **params,
                    },
                )
            else:
                return OrderError(
                    "Request Timeout",
                    {"symbol": symbol, "side": side, "amount": amount, **params},
                )
        except Exception as e:
            return OrderError(
                e, {"symbol": symbol, "side": side, "amount": amount, **params}
            )

    async def place_market_order_ws(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        amount: Decimal,
        handle_timeout: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        try:
            res = await self._exchange.api.create_order_ws(
                symbol=symbol,
                type="market",
                side=side,
                amount=amount,
                params=kwargs,
            )
            return res
        except RequestTimeout:
            if handle_timeout:
                return await self.handle_request_timeout(
                    "place_market_order_ws",
                    {
                        "symbol": symbol,
                        "side": side,
                        "amount": amount,
                        "price": None,
                        **kwargs,
                    },
                )
            else:
                return OrderError(
                    "Request Timeout",
                    {"symbol": symbol, "side": side, "amount": amount, **kwargs},
                )
        except Exception as e:
            return OrderError(
                e, {"symbol": symbol, "side": side, "amount": amount, **kwargs}
            )

    async def cancel_order(
        self, id: str, symbol: str, handle_timeout: bool = True, **params
    ) -> Dict[str, Any]:  # 修改此行
        try:
            res = await self._exchange.api.cancel_order(id, symbol, params=params)
            return res
        except RequestTimeout:
            if handle_timeout:
                return await self.handle_request_timeout(
                    "cancel_order", {"id": id, "symbol": symbol, **params}
                )
            else:
                return OrderError(
                    "Request Timeout", {"id": id, "symbol": symbol, **params}
                )
        except Exception as e:
            return OrderError(e, {"id": id, "symbol": symbol, **params})

    async def cancel_order_ws(
        self, id: str, symbol: str, handle_timeout: bool = True, **params
    ) -> Dict[str, Any]:  # 修改此行
        try:
            res = await self._exchange.api.cancel_order_ws(id, symbol, params=params)
            return res
        except RequestTimeout:
            if handle_timeout:
                res = await self.handle_request_timeout(
                    "cancel_order_ws", {"id": id, "symbol": symbol, **params}
                )
                return res
            else:
                return OrderError(
                    "Request Timeout", {"id": id, "symbol": symbol, **params}
                )
        except Exception as e:
            return OrderError(e, {"id": id, **params})


# archive
class WebsocketManager(ABC):
    def __init__(
        self,
        base_url: str,
        ping_interval: int = 5,
        ping_timeout: int = 5,
        close_timeout: int = 1,
        max_queue: int = 12,
    ):
        self._base_url = base_url
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout
        self._close_timeout = close_timeout
        self._max_queue = max_queue

        self._tasks: List[asyncio.Task] = []
        self._subscripions = defaultdict(asyncio.Queue)
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="INFO", flush=True
        )

    async def _consume(
        self, subscription_id: str, callback: Callable[..., Any] = None, *args, **kwargs
    ):
        while True:
            msg = await self._subscripions[subscription_id].get()
            if asyncio.iscoroutinefunction(callback):
                await callback(msg, *args, **kwargs)
            else:
                callback(msg, *args, **kwargs)
            self._subscripions[subscription_id].task_done()

    @abstractmethod
    async def _subscribe(self, symbol: str, typ: str, channel: str, queue_id: str):
        pass

    async def close(self):
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._log.info("All WebSocket connections closed.")


class Listener(WSListener):
    def __init__(self, logger, specific_ping_msg=None):
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
        limiter: Limiter,
        handler: Callable[..., Any],
        specific_ping_msg: bytes = None,
        reconnect_interval: int = 0.2,
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
        self._task_manager = TaskManager()
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
        await self._limiter.wait()
        self._transport.send(WSMsgType.TEXT, orjson.dumps(payload))

    async def _msg_handler(self, queue: asyncio.Queue):
        while True:
            msg = await queue.get()
            self._callback(msg)
            queue.task_done()

    async def disconnect(self):
        if self.connected:
            self._transport.disconnect()
            await self._task_manager.cancel()

    @abstractmethod
    async def _resubscribe(self):
        pass


class RestApi:
    def __init__(self, **client_kwargs):
        self._session = None
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="INFO", flush=True
        )
        self._client_kwargs = client_kwargs
        self._loop = asyncio.get_event_loop()
        self._ssl_context = ssl.create_default_context(cafile=certifi.where())

    def init_session(self):
        if self._session is None:
            tcp_connector = aiohttp.TCPConnector(
                ssl=self._ssl_context, loop=self._loop, enable_cleanup_closed=True
            )
            self._session = aiohttp.ClientSession(
                loop=self._loop,
                connector=tcp_connector,
                json_serialize=orjson.dumps,
                **self._client_kwargs,
            )

    async def close_session(self):
        if self._session:
            await self._session.close()

    async def _parse_response(self, response: aiohttp.ClientResponse) -> Any:
        if "application/json" in response.headers.get("Content-Type", ""):
            return await response.json()
        else:
            return await response.text()

    async def request(self, method: str, url: str, **kwargs) -> Any:
        """
        Perform an HTTP request without using async context managers.

        :param method: HTTP method (GET, POST, PUT, DELETE, etc.).
        :param url: The URL for the request. If base_url is set, this can be a relative path.
        :param kwargs: Additional arguments for the request (e.g., params, json, data).
        :return: The parsed JSON response or raw text based on response headers.
        :raises: ClientResponseError, ClientError, Exception
        """
        if self._session is None:
            self.init_session()

        try:
            response = await self._session.request(method, url, **kwargs)
            data = await self._parse_response(response)
            response.raise_for_status()

            self._log.debug(
                f"Request {method} {url} succeeded with status {response.status}, kwargs: {kwargs}"
            )
            return data

        except ClientResponseError as e:
            self._log.error(
                f"ClientResponseError: {str(e)} for URL: {url}, kwargs: {kwargs}"
            )
            raise ExchangeResponseError(e.message, data, method, url) from None
        except ClientError as e:
            self._log.error(f"ClientError: {str(e)} for URL: {url}, kwargs: {kwargs}")
            raise
        except asyncio.TimeoutError:
            self._log.error(f"RequestTimeout for URL: {url}, kwargs: {kwargs}")
            raise
        except Exception as e:
            self._log.error(f"Exception: {str(e)} for URL: {url}, kwargs: {kwargs}")
            raise

    async def get(self, url: str, **kwargs) -> Any:
        """
        Perform an HTTP GET request.

        :param url: The URL for the GET request.
        :param kwargs: Additional arguments for the request.
        :return: The response data.
        """
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> Any:
        """
        Perform an HTTP POST request.

        :param url: The URL for the POST request.
        :param kwargs: Additional arguments for the request.
        :return: The response data.
        """
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> Any:
        """
        Perform an HTTP PUT request.

        :param url: The URL for the PUT request.
        :param kwargs: Additional arguments for the request.
        :return: The response data.
        """
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> Any:
        """
        Perform an HTTP DELETE request.

        :param url: The URL for the DELETE request.
        :param kwargs: Additional arguments for the request.
        :return: The response data.
        """
        return await self.request("DELETE", url, **kwargs)


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
        self._init_session()

    def _init_session(self):
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


class Clock:
    def __init__(self, tick_size: float = 1.0):
        """
        :param tick_size_s: Time interval of each tick in seconds (supports sub-second precision).
        """
        self._tick_size = tick_size  # Tick size in seconds
        self._current_tick = (time.time() // self._tick_size) * self._tick_size
        self._clock = LiveClock()
        self._tick_callbacks: List[Callable[[float], None]] = []
        self._started = False

    @property
    def tick_size(self) -> float:
        return self._tick_size

    @property
    def current_timestamp(self) -> float:
        return self._clock.timestamp()

    def add_tick_callback(self, callback: Callable[[float], None]):
        """
        Register a callback to be called on each tick.
        :param callback: Function to be called with current_tick as argument.
        """
        self._tick_callbacks.append(callback)

    async def run(self):
        if self._started:
            raise RuntimeError("Clock is already running.")
        self._started = True
        while True:
            now = time.time()
            next_tick_time = self._current_tick + self._tick_size
            sleep_duration = next_tick_time - now
            if sleep_duration > 0:
                await asyncio.sleep(sleep_duration)
            else:
                # If we're behind schedule, skip to the next tick to prevent drift
                next_tick_time = now
            self._current_tick = next_tick_time
            for callback in self._tick_callbacks:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self.current_timestamp)
                else:
                    callback(self.current_timestamp)


class PublicConnector(ABC):
    def __init__(
        self,
        account_type,
        market: Dict[str, BaseMarket],
        market_id: Dict[str, BaseMarket],
        exchange_id: str,
        ws_client: WSClient,
    ):
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )
        self._account_type = account_type
        self._market = market
        self._market_id = market_id
        self._exchange_id = exchange_id
        self._ws_client = ws_client

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
        await self._ws_client.disconnect()


class PrivateConnector(ABC):
    def __init__(
        self,
        account_type,
        market: Dict[str, BaseMarket],
        market_id: Dict[str, BaseMarket],
        exchange_id: str,
        ws_client: WSClient,
        cache: AsyncCache,
        rate_limit: float = None,
    ):
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )
        self._account_type = account_type
        self._market = market
        self._market_id = market_id
        self._exchange_id = exchange_id
        self._task_manager = TaskManager()
        self._ws_client = ws_client
        self._clock = LiveClock()
        self._cache = cache
        self._oms = OrderManagerSystem(cache)
        
        if rate_limit:
            self._limiter = Limiter(rate_limit)
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

    async def connect(self):
        await self._cache.sync()

    async def disconnect(self):
        await self._cache.close()
        await self._ws_client.disconnect()
        await self._task_manager.cancel()

    def amount_to_precision(
        self,
        symbol: str,
        amount: float,
        mode: Literal["round", "ceil", "floor"] = "round",
    ) -> Decimal:
        market = self._market[symbol]
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
        market = self._market[symbol]
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



class OrderManagerSystem:
    def __init__(self, cache: AsyncCache):
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )
        self._cache = cache
        self._order_msg_queue: asyncio.Queue[Order] = asyncio.Queue()

    def add_order_msg(self, order: Order):
        self._order_msg_queue.put_nowait(order)

    async def handle_order_event(self):
        while True:
            try:
                order = await self._order_msg_queue.get()
                match order.status:
                    case OrderStatus.PENDING:
                        self._log.debug(f"ORDER STATUS PENDING: {str(order)}")
                        valid = self._cache.order_initialized(order)
                    case OrderStatus.CANCELING:
                        self._log.debug(f"ORDER STATUS CANCELING: {str(order)}")
                        valid = self._cache.order_status_update(order)
                    case OrderStatus.ACCEPTED:
                        self._log.debug(f"ORDER STATUS ACCEPTED: {str(order)}")
                        valid = self._cache.order_status_update(order)
                        EventSystem.emit(OrderStatus.ACCEPTED, order)
                    case OrderStatus.PARTIALLY_FILLED:
                        self._log.debug(f"ORDER STATUS PARTIALLY FILLED: {str(order)}")
                        valid = self._cache.order_status_update(order)
                        EventSystem.emit(OrderStatus.PARTIALLY_FILLED, order)
                    case OrderStatus.CANCELED:
                        self._log.debug(f"ORDER STATUS CANCELED: {str(order)}")
                        valid = self._cache.order_status_update(order)
                        EventSystem.emit(OrderStatus.CANCELED, order)
                    case OrderStatus.FILLED:
                        self._log.debug(f"ORDER STATUS FILLED: {str(order)}")
                        valid = self._cache.order_status_update(order)
                        EventSystem.emit(OrderStatus.FILLED, order)
                    case OrderStatus.EXPIRED:
                        self._log.debug(f"ORDER STATUS EXPIRED: {str(order)}")
                        valid = self._cache.order_status_update(order)
                if valid:
                    await self._cache.apply_position(order)
                self._order_msg_queue.task_done()
            except Exception as e:
                self._log.error(f"Error in handle_order_event: {e}")
