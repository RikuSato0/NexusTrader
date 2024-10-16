import asyncio
import orjson

import aiosonic
import ccxt.pro as ccxtpro


from abc import ABC, abstractmethod
from typing import Dict, List, Any
from typing import Callable, Literal
from collections import defaultdict
from decimal import Decimal
from urllib.parse import urlparse

from asynciolimiter import Limiter
from ccxt.base.errors import RequestTimeout


from tradebot.log import SpdLog
from tradebot.exceptions import OrderError
from picows import (
    ws_connect,
    WSFrame,
    WSTransport,
    WSListener,
    WSMsgType,
)


class ExchangeManager(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api = self._init_exchange()
        self.market = None

    def _init_exchange(self) -> ccxtpro.Exchange:
        try:
            exchange_class = getattr(ccxtpro, self.config["exchange_id"])
        except AttributeError:
            raise AttributeError(
                f"Exchange {self.config['exchange_id']} is not supported"
            )

        api = exchange_class(self.config)
        api.set_sandbox_mode(
            self.config.get("sandbox", False)
        )  # Set sandbox mode if demo trade is enabled
        return api

    async def load_markets(self):
        self.market = await self.api.load_markets()
        return self.market

    async def close(self):
        await self.api.close()


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


class WSClient(WSListener):
    def __init__(self, logger):
        self._log = logger
        self.msg_queue = asyncio.Queue()

    def on_ws_connected(self, transport: WSTransport):
        self._log.info("Connected to Websocket...")

    def on_ws_disconnected(self, transport: WSTransport):
        self._log.info("Disconnected from Websocket.")

    def on_ws_frame(self, transport: WSTransport, frame: WSFrame):
        if frame.msg_type == WSMsgType.PING:
            transport.send_pong(frame.get_payload_as_bytes())
            return
        msg = orjson.loads(frame.get_payload_as_bytes())
        self.msg_queue.put_nowait(msg)


class WSManager(ABC):
    def __init__(self, url: str, limiter: Limiter):
        self._url = url
        self._reconnect_interval = 0.2  # Reconnection interval in seconds
        self._ping_idle_timeout = 2
        self._ping_reply_timeout = 1
        self._listener = None
        self._transport = None
        self._subscriptions = {}
        self._limiter = limiter
        self._msg_handler_task = None
        self._connection_handler_task = None
        self._log = SpdLog.get_logger(type(self).__name__, level="INFO", flush=True)

    @property
    def connected(self):
        return self._transport and self._listener

    async def _connect(self):
        WSClientFactory = lambda: WSClient(self._log)  # noqa: E731
        self._transport, self._listener = await ws_connect(
            WSClientFactory,
            self._url,
            enable_auto_ping=True,
            auto_ping_idle_timeout=self._ping_idle_timeout,
            auto_ping_reply_timeout=self._ping_reply_timeout,
        )

    async def connect(self):
        if not self.connected:
            await self._connect()
            self._msg_handler_task = asyncio.create_task(
                self._msg_handler(self._listener.msg_queue)
            )
            self._connection_handler_task = asyncio.create_task(
                self._connection_handler()
            )

    async def _connection_handler(self):
        while True:
            try:
                if not self.connected:
                    await self._connect()
                    self._msg_handler_task = asyncio.create_task(
                        self._msg_handler(self._listener.msg_queue)
                    )
                    await self._resubscribe()
                await self._transport.wait_disconnected()
            except Exception as e:
                self._log.error(f"Connection error: {e}")
            finally:
                self._log.info("Websocket reconnecting...")
                if self._msg_handler_task:
                    self._msg_handler_task.cancel()
                self._transport, self._listener = None, None
                await asyncio.sleep(self._reconnect_interval)

    def _send(self, payload: dict):
        self._transport.send(WSMsgType.TEXT, orjson.dumps(payload))

    async def _resubscribe(self):
        for _, payload in self._subscriptions.items():
            await self._limiter.wait()
            self._send(payload)

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
    def _callback(self, msg):
        pass


class AsyncHttpRequests(object):
    """Asynchronous HTTP Request Client."""

    # Every domain name holds a connection client, for less system resource utilization and faster request speed.
    _CLIENTS = {}  # {"domain-name": client, ... }
    _log = SpdLog.get_logger(name="AsyncHttpRequests", level="INFO", flush=True)

    @classmethod
    async def fetch(
        cls,
        method,
        url,
        params=None,
        body=None,
        data=None,
        headers=None,
        timeout=30,
        **kwargs,
    ):
        """Create a HTTP request.

        Args:
            method: HTTP request method. `GET` / `POST` / `PUT` / `DELETE`
            url: Request url.
            params: HTTP query params.
            body: HTTP request body, string or bytes format.
            data: HTTP request body, dict format.
            headers: HTTP request header.
            timeout: HTTP request timeout(seconds), default is 30s.

            kwargs:
                proxy: HTTP proxy.

        Return:
            code: HTTP response code.
            success: HTTP response data. If something wrong, this field is None.
            error: If something wrong, this field will holding a Error information, otherwise it's None.

        Raises:
            HTTP request exceptions or response data parse exceptions. All the exceptions will be captured and return
            Error information.
        """
        client = cls._get_client(url)
        try:
            if method == "GET":
                response = await client.get(
                    url,
                    params=params,
                    headers=headers,
                    timeouts=aiosonic.timeout.Timeouts(sock_read=timeout),
                    **kwargs,
                )
            elif method == "POST":
                response = await client.post(
                    url,
                    params=params,
                    data=body,
                    json=data,
                    headers=headers,
                    timeouts=aiosonic.timeout.Timeouts(sock_read=timeout),
                    **kwargs,
                )
            elif method == "PUT":
                response = await client.put(
                    url,
                    params=params,
                    data=body,
                    json=data,
                    headers=headers,
                    timeouts=aiosonic.timeout.Timeouts(sock_read=timeout),
                    **kwargs,
                )
            elif method == "DELETE":
                response = await client.delete(
                    url,
                    params=params,
                    data=body,
                    json=data,
                    headers=headers,
                    timeouts=aiosonic.timeout.Timeouts(sock_read=timeout),
                    **kwargs,
                )
            else:
                error = "HTTP method error!"
                return None, None, error
        except Exception as e:
            cls._log.error(
                f"Method: {method}, URL: {url}, Headers: {headers}, Params: {params}, "
                f"Body: {body}, Data: {data}, Error: {e}"
            )
            return None, None, e
        code = response.status_code
        if code not in (200, 201, 202, 203, 204, 205, 206):
            text = await response.text()
            cls._log.error(
                f"Method: {method}, URL: {url}, Headers: {headers}, Params: {params}, "
                f"Body: {body}, Data: {data}, Code: {code}, Result: {text}"
            )
            return code, None, text
        try:
            result = await response.json()
        except Exception as e:
            result = await response.text()
            cls._log.warn(
                "Response data is not JSON format!",
                f"Method: {method}, URL: {url}, Headers: {headers}, Params: {params}, "
                f"Body: {body}, Data: {data}, Code: {code}, Result: {result}",
            )
        cls._log.debug(
            f"Method: {method}, URL: {url}, Headers: {headers}, Params: {params}, "
            f"Body: {body}, Data: {data}, Code: {code}, Result: {result}"
        )
        return code, result, None

    @classmethod
    async def get(
        cls, url, params=None, body=None, data=None, headers=None, timeout=30, **kwargs
    ):
        """HTTP GET"""
        result = await cls.fetch(
            "GET", url, params, body, data, headers, timeout, **kwargs
        )
        return result

    @classmethod
    async def post(
        cls, url, params=None, body=None, data=None, headers=None, timeout=30, **kwargs
    ):
        """HTTP POST"""
        result = await cls.fetch(
            "POST", url, params, body, data, headers, timeout, **kwargs
        )
        return result

    @classmethod
    async def delete(
        cls, url, params=None, body=None, data=None, headers=None, timeout=30, **kwargs
    ):
        """HTTP DELETE"""
        result = await cls.fetch(
            "DELETE", url, params, body, data, headers, timeout, **kwargs
        )
        return result

    @classmethod
    async def put(
        cls, url, params=None, body=None, data=None, headers=None, timeout=30, **kwargs
    ):
        """HTTP PUT"""
        result = await cls.fetch(
            "PUT", url, params, body, data, headers, timeout, **kwargs
        )
        return result

    @classmethod
    def _get_client(cls, url):
        """Get the connection client for url's domain, if no client, create a new.

        Args:
            url: HTTP request url.

        Returns:
            client: HTTP request client.
        """
        parsed_url = urlparse(url)
        key = parsed_url.netloc or parsed_url.hostname
        if key not in cls._CLIENTS:
            proxy = cls.config.get("proxy")
            if proxy:
                client = aiosonic.HTTPClient(proxy=aiosonic.Proxy(proxy))
            else:
                client = aiosonic.HTTPClient()
            cls._CLIENTS[key] = client
        return cls._CLIENTS[key]
