import asyncio
import socket

from collections import defaultdict
from typing import Callable, Optional, Type
from typing import Dict, List, Any, Set

import redis
import msgspec

from tradebot.types import Position
from tradebot.constants import get_redis_config
from tradebot.constants import STATUS_TRANSITIONS
from tradebot.constants import OrderStatus, AccountType
from tradebot.types import Order
from tradebot.log import SpdLog

from tradebot.core.nautilius_core import LiveClock


class TaskManager:
    def __init__(self):
        self._tasks: List[asyncio.Task] = []

    def create_task(self, coro: asyncio.coroutines) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._tasks.append(task)
        task.add_done_callback(self._handle_task_done)
        return task

    def _handle_task_done(self, task: asyncio.Task):
        self._tasks.remove(task)
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception:
            raise

    async def cancel(self):
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)


class EventSystem:
    _listeners: Dict[str, List[Callable]] = defaultdict(list)

    @classmethod
    def on(cls, event: str, callback: Optional[Callable] = None):
        """
        Register an event listener. Can be used as a decorator or as a direct method.

        Usage as a method:
            EventSystem.on('order_update', callback_function)

        Usage as a decorator:
            @EventSystem.on('order_update')
            def callback_function(msg):
                ...
        """
        if callback is None:

            def decorator(fn: Callable):
                if event not in cls._listeners:
                    cls._listeners[event] = []
                cls._listeners[event].append(fn)
                return fn

            return decorator

        cls._listeners[event].append(callback)
        return callback  # Optionally return the callback for chaining

    @classmethod
    def emit(cls, event: str, *args: Any, **kwargs: Any):
        """
        Emit an event to all registered synchronous listeners.

        :param event: The event name.
        :param args: Positional arguments to pass to the listeners.
        :param kwargs: Keyword arguments to pass to the listeners.
        """
        for callback in cls._listeners.get(event, []):
            callback(*args, **kwargs)

    @classmethod
    async def aemit(cls, event: str, *args: Any, **kwargs: Any):
        """
        Asynchronously emit an event to all registered asynchronous listeners.

        :param event: The event name.
        :param args: Positional arguments to pass to the listeners.
        :param kwargs: Keyword arguments to pass to the listeners.
        """
        for callback in cls._listeners.get(event, []):
            await callback(*args, **kwargs)


class RedisClient:
    _params = None

    @classmethod
    def _is_in_docker(cls) -> bool:
        try:
            socket.gethostbyname("redis")
            return True
        except socket.gaierror:
            return False

    @classmethod
    def _get_params(cls) -> dict:
        if cls._params is None:
            in_docker = cls._is_in_docker()
            cls._params = get_redis_config(in_docker)
        return cls._params

    @classmethod
    def get_client(cls) -> redis.Redis:
        return redis.Redis(**cls._get_params())

    @classmethod
    def get_async_client(cls) -> redis.asyncio.Redis:
        return redis.asyncio.Redis(**cls._get_params())


class AsyncCache:
    def __init__(
        self,
        account_type: AccountType,
        strategy_id: str,
        user_id: str,
        sync_interval: int = 60,
        expire_time: int = 3600,
    ):
        self.strategy_id = strategy_id
        self.user_id = user_id
        self.account_type = account_type

        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )
        self._clock = LiveClock()
        self._r = RedisClient.get_async_client()
        self._orders_key = f"strategy:{strategy_id}:user_id:{user_id}:account_type:{account_type}:orders"
        self._open_orders_key = f"strategy:{strategy_id}:user_id:{user_id}:account_type:{account_type}:open_orders"
        self._symbol_open_orders_key = f"strategy:{strategy_id}:user_id:{user_id}:account_type:{account_type}:symbol_open_orders"
        self._symbol_orders_key = f"strategy:{strategy_id}:user_id:{user_id}:account_type:{account_type}:symbol_orders"
        self._symbol_positions_key = f"strategy:{strategy_id}:user_id:{user_id}:account_type:{account_type}:symbol_positions"

        # in-memory save
        self._mem_orders: Dict[str, Order] = {}  # order_id -> Order
        self._mem_open_orders: Set[str] = set()  # set(order_id)
        self._mem_symbol_open_orders: Dict[str, Set[str]] = defaultdict(
            set
        )  # symbol -> set(order_id)
        self._mem_symbol_orders: Dict[str, Set[str]] = defaultdict(
            set
        )  # symbol -> set(order_id)
        self._mem_symbol_positions: Dict[str, Position] = {}  # symbol -> Position

        # set params
        self._sync_interval = sync_interval  # sync interval
        self._expire_time = expire_time  # expire time

        self._shutdown_event = asyncio.Event()
        self._task_manager = TaskManager()

    def _encode(self, obj: Order | Position) -> bytes:
        return msgspec.json.encode(obj)

    def _decode(
        self, data: bytes, obj_type: Type[Order | Position]
    ) -> Order | Position:
        return msgspec.json.decode(data, type=obj_type)

    async def sync(self):
        self._task_manager.create_task(self._periodic_sync())

    async def _periodic_sync(self):
        while not self._shutdown_event.is_set():
            await self._sync_to_redis()
            self._cleanup_expired_data()
            await asyncio.sleep(self._sync_interval)

    async def _sync_to_redis(self):
        self._log.debug("syncing to redis")
        for order_id, order in self._mem_orders.copy().items():
            await self._r.hset(self._orders_key, order_id, self._encode(order))

        if await self._r.exists(self._open_orders_key):
            await self._r.delete(self._open_orders_key)

        if self._mem_open_orders:
            await self._r.sadd(self._open_orders_key, *self._mem_open_orders)

        for symbol, order_ids in self._mem_symbol_orders.copy().items():
            key = f"{self._symbol_orders_key}:{symbol}"
            await self._r.delete(key)
            if order_ids:
                await self._r.sadd(key, *order_ids)

        for symbol, order_ids in self._mem_symbol_open_orders.copy().items():
            key = f"{self._symbol_open_orders_key}:{symbol}"
            await self._r.delete(key)
            if order_ids:
                await self._r.sadd(key, *order_ids)

        # Add position sync
        for symbol, position in self._mem_symbol_positions.copy().items():
            key = f"{self._symbol_positions_key}:{symbol}"
            await self._r.set(key, self._encode(position))

    def _cleanup_expired_data(self):
        current_time = self._clock.timestamp_ms()
        expire_before = current_time - self._expire_time * 1000

        # 清理过期orders
        expired_orders = [
            order_id
            for order_id, order in self._mem_orders.copy().items()
            if order.timestamp < expire_before
        ]
        for order_id in expired_orders:
            del self._mem_orders[order_id]
            self._log.debug(f"removing order {order_id} from memory")
            for symbol, order_set in self._mem_symbol_orders.copy().items():
                self._log.debug(f"removing order {order_id} from symbol {symbol}")
                order_set.discard(order_id)

    def _check_status_transition(self, order: Order):
        previous_order = self._mem_orders.get(order.id)
        if not previous_order:
            return True

        if order.status not in STATUS_TRANSITIONS[previous_order.status]:
            self._log.error(
                f"Invalid status transition: {previous_order.status} -> {order.status}"
            )
            return False

        return True

    async def apply_position(self, order: Order):
        symbol = order.symbol
        if symbol not in self._mem_symbol_positions:
            position = await self.get_position(symbol)
            if not position:
                position = Position(
                    symbol=symbol,
                    exchange=order.exchange,
                    strategy_id=self.strategy_id,
                )
            self._mem_symbol_positions[symbol] = position
        if order.status in (
            OrderStatus.FILLED,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.CANCELED,
        ):
            self._log.debug(
                f"POSITION UPDATED: status {order.status} order_id {order.id} side {order.side} filled: {order.filled} amount: {order.amount} reduceOnly: {order.reduce_only}"
            )
            self._mem_symbol_positions[symbol].apply(order)

    async def get_position(self, symbol: str) -> Position:
        # First try memory
        if position := self._mem_symbol_positions.get(symbol):
            return position

        # Then try Redis
        key = f"{self._symbol_positions_key}:{symbol}"
        if position_data := await self._r.get(key):
            position = self._decode(position_data, Position)
            self._mem_symbol_positions[symbol] = position  # Cache in memory
            return position

        return None

    def order_initialized(self, order: Order):
        if not self._check_status_transition(order):
            return
        self._mem_orders[order.id] = order
        self._mem_open_orders.add(order.id)
        self._mem_symbol_orders[order.symbol].add(order.id)
        self._mem_symbol_open_orders[order.symbol].add(order.id)

    def order_status_update(self, order: Order):
        if not self._check_status_transition(order):
            return

        self._mem_orders[order.id] = order
        if order.status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
            OrderStatus.EXPIRED,
        ):
            self._mem_open_orders.discard(order.id)
            self._mem_symbol_open_orders[order.symbol].discard(order.id)

    async def get_order(self, order_id: str) -> Order:
        if order_id in self._mem_orders:
            return self._mem_orders[order_id]

        raw_order = await self._r.hget(self._orders_key, order_id)
        if raw_order:
            order = self._decode(raw_order, Order)
            self._mem_orders[order_id] = order
            return order
        return None

    async def get_symbol_orders(self, symbol: str, in_mem: bool = True) -> Set[str]:
        """Get all orders for a symbol from memory and Redis"""

        memory_orders = self._mem_symbol_orders.get(symbol, set())
        if not in_mem:
            redis_orders = await self._r.smembers(f"{self._symbol_orders_key}:{symbol}")
            redis_orders = (
                {order_id.decode() for order_id in redis_orders}
                if redis_orders
                else set()
            )
            return memory_orders.union(redis_orders)
        return memory_orders

    async def get_open_orders(self, symbol: str = None) -> Set[str]:
        if symbol:
            return self._mem_symbol_open_orders.get(symbol, set())
        return self._mem_open_orders

    async def close(self):
        self._shutdown_event.set()
        await self._sync_to_redis()
        await self._r.aclose()
        await self._task_manager.cancel()
