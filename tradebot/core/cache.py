import msgspec
import asyncio

from typing import Dict, Set, Type, List, Optional
from collections import defaultdict
from returns.maybe import maybe

from tradebot.schema import (
    Order,
    Position,
    ExchangeType,
    InstrumentId,
    Kline,
    BookL1,
    Trade,
    AlgoOrder,
    AccountBalance,
    Balance,
)
from tradebot.constants import STATUS_TRANSITIONS, AccountType
from tradebot.core.entity import TaskManager, RedisClient
from tradebot.core.log import SpdLog
from tradebot.core.nautilius_core import LiveClock, MessageBus


class AsyncCache:
    def __init__(
        self,
        strategy_id: str,
        user_id: str,
        msgbus: MessageBus,
        task_manager: TaskManager,
        sync_interval: int = 60,  # seconds
        expire_time: int = 3600,  # seconds
    ):
        self.strategy_id = strategy_id
        self.user_id = user_id

        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )
        self._clock = LiveClock()
        self._r_async = RedisClient.get_async_client()
        self._r = RedisClient.get_client()

        # in-memory save
        self._mem_closed_orders: Dict[str, bool] = {}  # uuid -> bool
        self._mem_orders: Dict[str, Order] = {}  # uuid -> Order
        self._mem_algo_orders: Dict[str, AlgoOrder] = {}  # uuid -> AlgoOrder

        self._mem_open_orders: Dict[ExchangeType, Set[str]] = defaultdict(
            set
        )  # exchange_id -> set(uuid)
        self._mem_symbol_open_orders: Dict[str, Set[str]] = defaultdict(
            set
        )  # symbol -> set(uuid)
        self._mem_symbol_orders: Dict[str, Set[str]] = defaultdict(
            set
        )  # symbol -> set(uuid)
        self._mem_positions: Dict[str, Position] = {}  # symbol -> Position
        
        self._mem_account_balance: Dict[AccountType, AccountBalance] = defaultdict(AccountBalance)

        # set params
        self._sync_interval = sync_interval  # sync interval
        self._expire_time = expire_time  # expire time

        self._shutdown_event = asyncio.Event()
        self._task_manager = task_manager

        self._kline_cache: Dict[str, Kline] = {}
        self._bookl1_cache: Dict[str, BookL1] = {}
        self._trade_cache: Dict[str, Trade] = {}

        self._msgbus = msgbus
        self._msgbus.subscribe(topic="kline", handler=self._update_kline_cache)
        self._msgbus.subscribe(topic="bookl1", handler=self._update_bookl1_cache)
        self._msgbus.subscribe(topic="trade", handler=self._update_trade_cache)

    ################# # base functions ####################

    def _encode(self, obj: Order | Position | AlgoOrder) -> bytes:
        return msgspec.json.encode(obj)

    def _decode(
        self, data: bytes, obj_type: Type[Order | Position | AlgoOrder]
    ) -> Order | Position | AlgoOrder:
        return msgspec.json.decode(data, type=obj_type)

    async def start(self):
        self._task_manager.create_task(self._periodic_sync())

    async def _periodic_sync(self):
        while not self._shutdown_event.is_set():
            await self._sync_to_redis()
            self._cleanup_expired_data()
            await asyncio.sleep(self._sync_interval)

    async def _sync_to_redis(self):
        self._log.debug("syncing to redis")
        for uuid, order in self._mem_orders.copy().items():
            orders_key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:orders"
            await self._r_async.hset(orders_key, uuid, self._encode(order))
        
        for uuid, algo_order in self._mem_algo_orders.copy().items():
            algo_orders_key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:algo_orders"
            await self._r_async.hset(algo_orders_key, uuid, self._encode(algo_order))

        for exchange, open_order_uuids in self._mem_open_orders.copy().items():
            open_orders_key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:exchange:{exchange.value}:open_orders"

            await self._r_async.delete(open_orders_key)

            if open_order_uuids:
                await self._r_async.sadd(open_orders_key, *open_order_uuids)

        for symbol, uuids in self._mem_symbol_orders.copy().items():
            instrument_id = InstrumentId.from_str(symbol)
            key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:exchange:{instrument_id.exchange.value}:symbol_orders:{symbol}"
            await self._r_async.delete(key)
            if uuids:
                await self._r_async.sadd(key, *uuids)

        for symbol, uuids in self._mem_symbol_open_orders.copy().items():
            instrument_id = InstrumentId.from_str(symbol)
            key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:exchange:{instrument_id.exchange.value}:symbol_open_orders:{symbol}"
            await self._r_async.delete(key)
            if uuids:
                await self._r_async.sadd(key, *uuids)

        # Add position sync        
        for symbol, position in self._mem_positions.copy().items():
            key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:exchange:{position.exchange.value}:symbol_positions:{symbol}"
            await self._r_async.set(key, self._encode(position))

    def _cleanup_expired_data(self):
        current_time = self._clock.timestamp_ms()
        expire_before = current_time - self._expire_time * 1000

        # 清理过期orders
        expired_orders = [
            uuid
            for uuid, order in self._mem_orders.copy().items()
            if order.timestamp < expire_before
        ]
        for uuid in expired_orders:
            del self._mem_orders[uuid]
            self._mem_closed_orders.pop(uuid, None)
            self._log.debug(f"removing order {uuid} from memory")
            for symbol, order_set in self._mem_symbol_orders.copy().items():
                self._log.debug(f"removing order {uuid} from symbol {symbol}")
                order_set.discard(uuid)
        
        expired_algo_orders = [
            uuid
            for uuid, algo_order in self._mem_algo_orders.copy().items()
            if algo_order.timestamp < expire_before
        ]
        for uuid in expired_algo_orders:
            del self._mem_algo_orders[uuid]
            self._log.debug(f"removing algo order {uuid} from memory")

    async def close(self):
        self._shutdown_event.set()
        await self._sync_to_redis()
        await self._r_async.aclose()

    ################ # cache public data  ###################

    def _update_kline_cache(self, kline: Kline):
        self._kline_cache[kline.symbol] = kline

    def _update_bookl1_cache(self, bookl1: BookL1):
        self._bookl1_cache[bookl1.symbol] = bookl1

    def _update_trade_cache(self, trade: Trade):
        self._trade_cache[trade.symbol] = trade

    def kline(self, symbol: str) -> Kline | None:
        return self._kline_cache.get(symbol, None)

    def bookl1(self, symbol: str) -> BookL1 | None:
        return self._bookl1_cache.get(symbol, None)

    def trade(self, symbol: str) -> Trade | None:
        return self._trade_cache.get(symbol, None)

    ################ # cache private data  ###################

    def _check_status_transition(self, order: Order):
        previous_order = self._mem_orders.get(order.uuid)
        if not previous_order:
            return True

        if order.status not in STATUS_TRANSITIONS[previous_order.status]:
            self._log.error(
                f"Order id: {order.uuid} Invalid status transition: {previous_order.status} -> {order.status}"
            )
            return False

        return True
    
    def _apply_position(self, position: Position):
        self._mem_positions[position.symbol] = position
    
    def _apply_balance(self, account_type: AccountType, balances: List[Balance]):
        self._mem_account_balance[account_type]._apply(balances)
    
    def get_balance(self, account_type: AccountType) -> AccountBalance:
        return self._mem_account_balance[account_type]

    @maybe
    def get_position(self, symbol: str) -> Optional[Position]:
        # First try memory
        instrument_id = InstrumentId.from_str(symbol)
        if position := self._mem_positions.get(symbol, None):
            return position
            
        # Then try Redis
        key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:exchange:{instrument_id.exchange.value}:symbol_positions:{symbol}"
        if position_data := self._r.get(key):
            position = self._decode(position_data, Position)
            self._mem_positions[symbol] = position  # Cache in memory
            return position
        return None
    
    def get_all_positions(self, exchange: ExchangeType) -> Dict[str, Position]:
        positions = {symbol: position for symbol, position in self._mem_positions.copy().items() if position.exchange == exchange}
        
        key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:exchange:{exchange.value}:symbol_positions:*"
        if keys := self._r.keys(key):
            for position_key in keys:
                symbol = position_key.decode().split(":")[-1]
                if symbol in positions:
                    continue
                    
                if position_data := self._r.get(position_key):
                    position = self._decode(position_data, Position)
                    positions[symbol] = position
                    self._mem_positions[symbol] = position  # Cache in memory
        return positions
    
    

    def _order_initialized(self, order: Order | AlgoOrder):
        if isinstance(order, AlgoOrder):
            self._mem_algo_orders[order.uuid] = order
        else:
            if not self._check_status_transition(order):
                return
            self._mem_orders[order.uuid] = order
            self._mem_open_orders[order.exchange].add(order.uuid)
            self._mem_symbol_orders[order.symbol].add(order.uuid)
            self._mem_symbol_open_orders[order.symbol].add(order.uuid)

    def _order_status_update(self, order: Order | AlgoOrder):
        if isinstance(order, AlgoOrder):
            self._mem_algo_orders[order.uuid] = order
        else:
            if not self._check_status_transition(order):
                return
            self._mem_orders[order.uuid] = order
            if order.is_closed:
                self._mem_open_orders[order.exchange].discard(order.uuid)
                self._mem_symbol_open_orders[order.symbol].discard(order.uuid)

    @maybe
    def get_order(self, uuid: str) -> Optional[Order]:
        # find in memory first
        if uuid.startswith("ALGO-"):
            if order := self._mem_algo_orders.get(uuid):
                return order
            key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:algo_orders"
            obj_type = AlgoOrder
            mem_dict = self._mem_algo_orders
        else:
            if order := self._mem_orders.get(uuid):
                return order
            key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:orders"
            obj_type = Order
            mem_dict = self._mem_orders

        if raw_order := self._r.hget(key, uuid):
            order = self._decode(raw_order, obj_type)
            mem_dict[uuid] = order
            return order
        return None

    def get_symbol_orders(self, symbol: str, in_mem: bool = True) -> Set[str]:
        """Get all orders for a symbol from memory and Redis"""

        memory_orders = self._mem_symbol_orders.get(symbol, set())
        if not in_mem:
            instrument_id = InstrumentId.from_str(symbol)
            key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:exchange:{instrument_id.exchange.value}:symbol_orders:{symbol}"
            redis_orders: Set[bytes] = self._r.smembers(key)
            redis_orders = (
                {uuid.decode() for uuid in redis_orders} if redis_orders else set()
            )
            return memory_orders.union(redis_orders)
        return memory_orders

    def get_open_orders(
        self, symbol: str | None = None, exchange: ExchangeType | None = None
    ) -> Set[str]:
        if symbol is not None:
            return self._mem_symbol_open_orders[symbol]
        elif exchange is not None:
            return self._mem_open_orders[exchange]
        else:
            raise ValueError("Either `symbol` or `exchange` must be specified")
