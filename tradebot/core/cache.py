import msgspec
import asyncio

from typing import Dict, Set, Type
from collections import defaultdict


from tradebot.types import Order, Position, ExchangeType, InstrumentId
from tradebot.constants import OrderStatus, STATUS_TRANSITIONS
from tradebot.core.entity import TaskManager, RedisClient
from tradebot.core.log import SpdLog
from tradebot.core.nautilius_core import LiveClock


class AsyncCache:
    def __init__(
        self,
        strategy_id: str,
        user_id: str,
        task_manager: TaskManager,
        sync_interval: int = 60,
        expire_time: int = 3600,
    ):
        self.strategy_id = strategy_id
        self.user_id = user_id

        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )
        self._clock = LiveClock()
        self._r = RedisClient.get_async_client()

        # in-memory save
        self._mem_orders: Dict[str, Order] = {}  # order_id -> Order

        self._mem_open_orders: Dict[ExchangeType, Set[str]] = defaultdict(
            set
        )  # exchange_id -> set(order_id)
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
        self._task_manager = task_manager

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
            orders_key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:orders"
            await self._r.hset(orders_key, order_id, self._encode(order))

        for exchange, open_order_ids in self._mem_open_orders.copy().items():
            open_orders_key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:exchange:{exchange.value}:open_orders"

            await self._r.delete(open_orders_key)

            if open_order_ids:
                await self._r.sadd(open_orders_key, *open_order_ids)

        for symbol, order_ids in self._mem_symbol_orders.copy().items():
            instrument_id = InstrumentId.from_str(symbol)
            key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:exchange:{instrument_id.exchange.value}:symbol_orders:{symbol}"
            await self._r.delete(key)
            if order_ids:
                await self._r.sadd(key, *order_ids)

        for symbol, order_ids in self._mem_symbol_open_orders.copy().items():
            instrument_id = InstrumentId.from_str(symbol)
            key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:exchange:{instrument_id.exchange.value}:symbol_open_orders:{symbol}"
            await self._r.delete(key)
            if order_ids:
                await self._r.sadd(key, *order_ids)

        # Add position sync
        for symbol, position in self._mem_symbol_positions.copy().items():
            key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:exchange:{position.exchange.value}:symbol_positions:{symbol}"
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
        instrument_id = InstrumentId.from_str(symbol)
        key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:exchange:{instrument_id.exchange.value}:symbol_positions:{symbol}"
        if position_data := await self._r.get(key):
            position = self._decode(position_data, Position)
            self._mem_symbol_positions[symbol] = position  # Cache in memory
            return position

        return None

    def order_initialized(self, order: Order):
        if not self._check_status_transition(order):
            return
        self._mem_orders[order.id] = order
        self._mem_open_orders[order.exchange].add(order.id)
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
            self._mem_open_orders[order.exchange].discard(order.id)
            self._mem_symbol_open_orders[order.symbol].discard(order.id)

    async def get_order(self, order_id: str) -> Order:
        if order_id in self._mem_orders:
            return self._mem_orders[order_id]

        orders_key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:orders"
        raw_order = await self._r.hget(orders_key, order_id)
        if raw_order:
            order = self._decode(raw_order, Order)
            self._mem_orders[order_id] = order
            return order
        return None

    async def get_symbol_orders(self, symbol: str, in_mem: bool = True) -> Set[str]:
        """Get all orders for a symbol from memory and Redis"""

        memory_orders = self._mem_symbol_orders.get(symbol, set())
        if not in_mem:
            instrument_id = InstrumentId.from_str(symbol)
            key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:exchange:{instrument_id.exchange.value}:symbol_orders:{symbol}"
            redis_orders = await self._r.smembers(key)
            redis_orders = (
                {order_id.decode() for order_id in redis_orders}
                if redis_orders
                else set()
            )
            return memory_orders.union(redis_orders)
        return memory_orders

    async def get_open_orders(
        self, symbol: str | None = None, exchange: ExchangeType | None = None
    ) -> Set[str]:
        if symbol is not None:
            return self._mem_symbol_open_orders[symbol]
        elif exchange is not None:
            return self._mem_open_orders[exchange]
        else:
            raise ValueError("Either `symbol` or `exchange` must be specified")

    async def close(self):
        self._shutdown_event.set()
        await self._sync_to_redis()
        await self._r.aclose()
        await self._task_manager.cancel()
