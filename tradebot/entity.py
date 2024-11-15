import sys
import asyncio
import socket
import collections
import traceback

from pathlib import Path


from decimal import Decimal
from collections import defaultdict
from typing import Literal, Callable, Union, Optional
from typing import Dict, List, Any, Set
from dataclasses import dataclass, field, asdict

import redis
import orjson
import msgspec


from tradebot.constants import OrderStatus, AccountType
from tradebot.types import Order
from tradebot.log import SpdLog

from nautilus_trader.common.component import LiveClock


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
            if cls._is_in_docker():
                cls._params = {"host": "redis", "db": 0, "password": "password"}
            else:
                cls._params = {
                    "host": "localhost",
                    "port": 6379,
                    "db": 0,
                    "password": None,
                }
        return cls._params

    @classmethod
    def get_client(cls) -> redis.Redis:
        return redis.Redis(**cls._get_params())

    @classmethod
    def get_async_client(cls) -> redis.asyncio.Redis:
        return redis.asyncio.Redis(**cls._get_params())


@dataclass
class Account:
    def __init__(self, user: str, account_type: str, redis_client: redis.Redis):
        self.r = redis_client
        self.account_type = f"{user}:account:{account_type}"
        self.load_account()

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if key not in ["r", "account_type"]:
            self.r.hset(f"{self.account_type}", key, str(value))

    def __getattr__(self, key):
        if key not in ["r", "account_type"]:
            value = self.r.hget(f"{self.account_type}", key)
            if value is not None:
                return Decimal(value.decode())
            return Decimal("0")
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{key}'"
        )

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def keys(self):
        return [k for k in self.__dict__.keys() if k not in ["r", "account_type"]]

    def load_account(self):
        for key, value in self.r.hgetall(f"{self.account_type}").items():
            setattr(self, key.decode(), Decimal(value.decode()))


@dataclass
class Position:
    symbol: str = None
    amount: Decimal = Decimal("0")
    last_price: Decimal = Decimal("0")
    avg_price: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")

    def update(
        self,
        order_amount: Union[str, float, Decimal],
        order_price: Union[str, float, Decimal],
    ):
        order_amount = Decimal(str(order_amount))
        order_price = Decimal(str(order_price))

        self.total_cost += order_amount * order_price
        self.amount += order_amount
        self.avg_price = (
            self.total_cost / self.amount if self.amount != 0 else Decimal("0")
        )
        self.last_price = order_price

    @classmethod
    def from_dict(cls, data):
        return cls(
            symbol=data["symbol"],
            amount=Decimal(data["amount"]),
            last_price=Decimal(data["last_price"]),
            avg_price=Decimal(data["avg_price"]),
            total_cost=Decimal(data["total_cost"]),
        )

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "amount": str(self.amount),
            "last_price": str(self.last_price),
            "avg_price": str(self.avg_price),
            "total_cost": str(self.total_cost),
        }


class PositionDict:
    def __init__(self, user: str, redis_client: redis.Redis):
        self.user = user
        self.r = redis_client
        self.key = f"{user}:position"

    def __getitem__(self, symbol: str) -> Position:
        data = self.r.hget(self.key, symbol)
        if data:
            return Position.from_dict(orjson.loads(data))
        return Position(symbol=symbol)

    def __setitem__(self, symbol: str, position: Position):
        self.r.hset(self.key, symbol, orjson.dumps(position.to_dict()))

    def __delitem__(self, symbol: str):
        self.r.hdel(self.key, symbol)

    def __contains__(self, symbol: str):
        return self.r.hexists(self.key, symbol)

    def __iter__(self):
        return iter([k.decode("utf-8") for k in self.r.hkeys(self.key)])

    def update(
        self,
        symbol: str,
        order_amount: Union[str, float, Decimal],
        order_price: Union[str, float, Decimal],
    ):
        position = self[symbol]
        position.update(order_amount, order_price)

        if abs(position.amount) <= Decimal("1e-8"):
            del self[symbol]
        else:
            self[symbol] = position

    def items(self) -> Dict[str, Position]:
        all_positions = self.r.hgetall(self.key)
        return {
            k.decode(): Position.from_dict(orjson.loads(v))
            for k, v in all_positions.items()
        }

    def __repr__(self):
        return repr(self.items())

    @property
    def symbols(self):
        return list(self)


class Context:
    def __init__(self, user: str, redis_client: redis.Redis):
        self._redis_client = redis_client
        self._user = user
        self.portfolio_account = Account(
            user, "portfolio", self._redis_client
        )  # Portfolio-margin account
        self.position = PositionDict(user, self._redis_client)

    def __setattr__(self, name, value):
        if name in ["_redis_client", "_user", "portfolio_account", "position"]:
            super().__setattr__(name, value)
        else:
            self._redis_client.set(f"context:{self._user}:{name}", orjson.dumps(value))

    def __getattr__(self, name):
        if name in ["_redis_client", "_user", "portfolio_account", "position"]:
            return super().__getattr__(name)

        value = self._redis_client.get(f"context:{self._user}:{name}")
        if value is not None:
            return orjson.loads(value)
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )

    def clear(self, name: str = None):
        if name is None:
            for key in self._redis_client.keys(f"context:{self._user}:*"):
                self._redis_client.delete(key)
        else:
            self._redis_client.delete(f"context:{self._user}:{name}")


class RollingMedian:
    def __init__(self, n=10):
        self.n = n
        self.data = collections.deque(maxlen=n)

    def input(self, value):
        # if value not in self.data:
        self.data.append(value)

        if len(self.data) == self.n:
            return self.get_median()
        return 0

    def get_median(self):
        sorted_data = sorted(self.data)
        mid = len(sorted_data) // 2

        if len(sorted_data) % 2 == 0:
            return (sorted_data[mid - 1] + sorted_data[mid]) / 2.0
        else:
            return sorted_data[mid]


class RollingDiffSum:
    def __init__(self, n):
        self.n = n
        self.prev_price = None
        self.curr_price = None
        self.diffs = collections.deque(maxlen=n)

    def input(self, price):
        if self.curr_price is not None:
            diff = price - self.curr_price
            self.diffs.append(diff)

        self.prev_price = self.curr_price
        self.curr_price = price

        if len(self.diffs) == self.n:
            rolling_sum = sum(self.diffs)
            return rolling_sum
        else:
            return 0


@dataclass(slots=True)
class Quote:
    _ask: str = "0"
    _bid: str = "0"
    _ask_vol: str = "0"
    _bid_vol: str = "0"

    @property
    def ask(self) -> Decimal:
        return Decimal(self._ask)

    @ask.setter
    def ask(self, value: str):
        self._ask = value

    @property
    def bid(self) -> Decimal:
        return Decimal(self._bid)

    @bid.setter
    def bid(self, value: str):
        self._bid = value

    @property
    def ask_vol(self) -> Decimal:
        return Decimal(self._ask_vol)

    @ask_vol.setter
    def ask_vol(self, value: str):
        self._ask_vol = value

    @property
    def bid_vol(self) -> Decimal:
        return Decimal(self._bid_vol)

    @bid_vol.setter
    def bid_vol(self, value: str):
        self._bid_vol = value


class MarketDataStore:
    def __init__(self):
        self.quote = defaultdict(Quote)

    def update(self, symbol: str, ask: str, bid: str, ask_vol: str, bid_vol: str):
        self.quote[symbol] = Quote(ask=ask, bid=bid, ask_vol=ask_vol, bid_vol=bid_vol)


class LogRegister:
    """
    Log registration class responsible for creating and managing loggers.

    Features:
    - Supports multiple log levels
    - Structured log output (e.g., JSON format)
    - Captures and logs both synchronous and asynchronous exceptions
    - Supports log rotation
    - Log settings can be managed via configuration files or environment variables
    """

    def __init__(self, log_dir: str = ".logs", async_mode: bool = True):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.loggers = {}
        self.async_mode = async_mode

        self.setup_error_handling()

    def setup_error_handling(self):
        self.error_logger = self.get_logger("ERROR", level="ERROR", flush=True)

        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            tb_str = "".join(
                traceback.format_exception(exc_type, exc_value, exc_traceback)
            )
            self.error_logger.error(tb_str)

        sys.excepthook = handle_exception

        def handle_async_exception(loop, async_context):
            msg = async_context.get(
                "exception", async_context.get("message", "Unknown async exception")
            )
            if "exception" in async_context:
                exception = async_context["exception"]
                tb_str = "".join(
                    traceback.format_exception(
                        type(exception), exception, exception.__traceback__
                    )
                )
                self.error_logger.error(tb_str)
            else:
                self.error_logger.error(f"Caught async exception: {msg}")

        asyncio.get_event_loop().set_exception_handler(handle_async_exception)

    def get_logger(
        self,
        name: str,
        level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
        flush: bool = False,
    ) -> spd.Logger:
        """
        Get a logger with the specified name. Create a new one if it doesn't exist.

        :param name: Logger name
        :param level: Log level
        :param flush: Whether to flush after each log record
        :return: spdlog.Logger instance
        """
        if name not in self.loggers:
            logger_instance = spd.DailyLogger(
                name=name,
                filename=str(self.log_dir / f"{name}.log"),
                hour=0,
                minute=0,
                async_mode=self.async_mode,
            )
            logger_instance.set_level(self.parse_level(level))
            if flush:
                logger_instance.flush_on(self.parse_level(level))
            self.loggers[name] = logger_instance
        return self.loggers[name]

    def parse_level(
        self, level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    ) -> spd.LogLevel:
        """
        Parse log level string to spdlog.LogLevel.

        :param level: Log level string
        :return: spdlog.LogLevel
        """
        levels = {
            "DEBUG": spd.LogLevel.DEBUG,
            "INFO": spd.LogLevel.INFO,
            "WARNING": spd.LogLevel.WARN,
            "ERROR": spd.LogLevel.ERR,
            "CRITICAL": spd.LogLevel.CRITICAL,
        }
        return levels[level]

    def close_all_loggers(self):
        """
        Close all loggers and release resources.
        """
        for logger in self.loggers.values():
            logger.flush()
            logger.drop()

    def __del__(self):
        self.close_all_loggers()


class Cache:
    def __init__(self, account_type: AccountType, strategy_id: str, user_id: str):
        self._r = RedisClient.get_client()
        self._orders = f"strategy:{strategy_id}:user_id:{user_id}:account_type:{account_type}:orders"
        self._open_orders = f"strategy:{strategy_id}:user_id:{user_id}:account_type:{account_type}:open_orders"
        self._symbol_orders = f"strategy:{strategy_id}:user_id:{user_id}:account_type:{account_type}:symbol_orders"

    def _encode_order(self, order: Order) -> bytes:
        return msgspec.json.encode(order)

    def _decode_order(self, data: bytes) -> Order:
        return msgspec.json.decode(data, type=Order)

    def order_initialized(self, order: Order):
        if self._r.hget(self._orders, order.id):
            return
        self._r.hset(self._orders, order.id, self._encode_order(order))
        self._r.sadd(self._open_orders, order.id)
        self._r.sadd(f"{self._symbol_orders}:{order.symbol}", order.id)

    def order_status_update(self, order: Order):
        self._r.hset(self._orders, order.id, self._encode_order(order))

        if order.status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
            OrderStatus.EXPIRED,
        ):
            self._r.srem(self._open_orders, order.id)

    def get_order(self, order_id: str) -> Order:
        order_data = self._r.hget(self._orders, order_id)
        if order_data:
            return self._decode_order(order_data)
        return None

    def get_symbol_orders(self, symbol: str) -> Set[str]:
        orders = self._r.smembers(f"{self._symbol_orders}:{symbol}")
        if orders:
            return {order_id.decode() for order_id in orders}
        return set()

    def get_open_orders(self, symbol: str = None) -> Set[str]:
        orders = {
            order_id.decode() for order_id in self._r.smembers(self._open_orders) or []
        }
        if symbol:
            symbol_orders = self.get_symbol_orders(symbol)
            return orders.intersection(symbol_orders)
        return orders


# log_register = LogRegister()
# market = MarketDataStore()


class AsyncCache:
    def __init__(
        self,
        account_type: AccountType,
        strategy_id: str,
        user_id: str,
        sync_interval: int = 300,
        expire_time: int = 3600,
    ):
        self._clock = LiveClock()
        self._r = RedisClient.get_async_client()
        self._orders_key = f"strategy:{strategy_id}:user_id:{user_id}:account_type:{account_type}:orders"
        self._open_orders_key = f"strategy:{strategy_id}:user_id:{user_id}:account_type:{account_type}:open_orders"
        self._symbol_open_orders_key = f"strategy:{strategy_id}:user_id:{user_id}:account_type:{account_type}:symbol_open_orders"
        self._symbol_orders_key = f"strategy:{strategy_id}:user_id:{user_id}:account_type:{account_type}:symbol_orders"

        # in-memory save
        self._mem_orders: Dict[str, Order] = {}  # order_id -> Order
        self._mem_open_orders: Set[str] = set()  # set(order_id)
        self._mem_symbol_open_orders: Dict[str, Set[str]] = defaultdict(
            set
        )  # symbol -> set(order_id)
        self._mem_symbol_orders: Dict[str, Set[str]] = defaultdict(
            set
        )  # symbol -> set(order_id)

        # set params
        self._sync_interval = sync_interval  # sync interval
        self._expire_time = expire_time  # expire time

        self._shutdown_event = asyncio.Event()
        self._task_manager = TaskManager()

    def _encode_order(self, order: Order) -> bytes:
        return msgspec.json.encode(order)

    def _decode_order(self, data: bytes) -> Order:
        return msgspec.json.decode(data, type=Order)

    async def sync(self):
        self._task_manager.create_task(self._periodic_sync())
        self._task_manager.create_task(self._periodic_cleanup())

    async def _periodic_sync(self):
        while not self._shutdown_event.is_set():
            await self._sync_to_redis()
            await asyncio.sleep(self._sync_interval)
            await self._sync_to_redis()

    async def _periodic_cleanup(self):
        while not self._shutdown_event.is_set():
            self._cleanup_expired_data()
            await asyncio.sleep(self._sync_interval)

    async def _sync_to_redis(self):
        for order_id, order in self._mem_orders.items():
            self._log.debug(f"syncing order {order_id} to redis")
            await self._r.hset(self._orders_key, order_id, self._encode_order(order))

        await self._r.delete(self._open_orders_key)
        if self._mem_open_orders:
            await self._r.sadd(self._open_orders_key, *self._mem_open_orders)

        for symbol, order_ids in self._mem_symbol_orders.items():
            key = f"{self._symbol_orders_key}:{symbol}"
            await self._r.delete(key)
            if order_ids:
                await self._r.sadd(key, *order_ids)

        for symbol, order_ids in self._mem_symbol_open_orders.items():
            key = f"{self._symbol_open_orders_key}:{symbol}"
            await self._r.delete(key)
            if order_ids:
                await self._r.sadd(key, *order_ids)

    def _cleanup_expired_data(self):
        current_time = self._clock.timestamp()
        expire_before = current_time - self._expire_time

        # 清理过期orders
        expired_orders = [
            order_id
            for order_id, order in self._mem_orders.items()
            if order.timestamp < expire_before
        ]
        for order_id in expired_orders:
            del self._mem_orders[order_id]
            self._log.debug(f"removing order {order_id} from memory")
            for symbol, order_set in self._mem_symbol_orders.items():
                self._log.debug(f"removing order {order_id} from symbol {symbol}")
                order_set.discard(order_id)

    def order_initialized(self, order: Order):
        if (
            order.id in self._mem_orders
        ):  # which means the order is already pushed by websocket
            return
        self._mem_orders[order.id] = order
        self._mem_open_orders.add(order.id)
        self._mem_symbol_orders[order.symbol].add(order.id)
        self._mem_symbol_open_orders[order.symbol].add(order.id)

    def order_status_update(self, order: Order):
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
            order = self._decode_order(raw_order)
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
