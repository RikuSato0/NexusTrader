import asyncio
import orjson


import ccxt.pro as ccxtpro


from abc import ABC, abstractmethod
from typing import Dict, List, Any
from typing import Callable, Literal
from collections import defaultdict
from decimal import Decimal


from asynciolimiter import Limiter
from ccxt.base.errors import RequestTimeout


from tradebot.log import SpdLog
from tradebot.entity import Order
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
        self._log.info("Connected to Websocket.")

    def on_ws_disconnected(self, transport: WSTransport):
        self._log.info("Disconnected from Websocket.")

    def on_ws_frame(self, transport: WSTransport, frame: WSFrame):
        if frame.msg_type == WSMsgType.PING:
            transport.send_pong(frame.get_payload_as_bytes())
            return
        msg = orjson.loads(frame.get_payload_as_bytes())
        self.msg_queue.put_nowait(msg)
        


class WSManager:
    def __init__(self, url: str, limiter: Limiter):
        self._url = url
        self._reconnect_interval = 0.2  # Reconnection interval in seconds
        self._ping_idle_timeout = 2
        self._ping_reply_timeout = 1
        self._listener = None
        self._transport = None
        self._subscriptions = {}
        self._limiter = limiter
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
            asyncio.create_task(self._msg_handler())
            

    async def _connection_handler(self):
        while True:
            try:
                if not self.connected:
                    await self._connect()
                    await self._resubscribe()
                else:
                    await self._transport.wait_disconnected()
            except Exception as e:
                self._log.error(f"Connection error: {e}")
            finally:
                self._transport, self._listener = None, None
                await asyncio.sleep(self._reconnect_interval)
    
    async def _resubscribe(self):
        for _, payload in self._subscriptions.items():
            await self._limiter.wait()
            self._send(payload)
        

    def _send(self, payload: dict):
        self._transport.send(WSMsgType.TEXT, orjson.dumps(payload))


    async def _msg_handler(self):
        while True:
            msg = await self._listener.msg_queue.get()
            # TODO: handle different event types of messages
            self._callback(msg)
            self._listener.msg_queue.task_done()
    
    @abstractmethod
    def _callback(self, msg: dict):
        pass
