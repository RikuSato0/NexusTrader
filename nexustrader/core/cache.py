import msgspec
import asyncio
import aiosqlite
import sqlite3

from typing import Dict, Set, Type, List, Optional
from collections import defaultdict
from returns.maybe import maybe
from pathlib import Path

from nexustrader.schema import (
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
from nexustrader.constants import STATUS_TRANSITIONS, AccountType, KlineInterval
from nexustrader.core.entity import TaskManager, RedisClient
from nexustrader.core.log import SpdLog
from nexustrader.core.nautilius_core import LiveClock, MessageBus
from nexustrader.constants import StorageBackend

class AsyncCache:
    def __init__(
        self,
        strategy_id: str,
        user_id: str,
        msgbus: MessageBus,
        task_manager: TaskManager,
        storage_backend: StorageBackend = StorageBackend.REDIS,
        db_path: str = "cache.db",
        sync_interval: int = 60,  # seconds
        expire_time: int = 3600,  # seconds
    ):
        self.strategy_id = strategy_id
        self.user_id = user_id
        self._storage_backend = storage_backend
        self._db_path = db_path

        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )
        self._clock = LiveClock()

        # in-memory save
        self._mem_closed_orders: Dict[str, bool] = {}  # uuid -> bool
        self._mem_orders: Dict[str, Order] = {}  # uuid -> Order
        self._mem_algo_orders: Dict[str, AlgoOrder] = {}  # uuid -> AlgoOrder
        self._mem_open_orders: Dict[ExchangeType, Set[str]] = defaultdict(set)  # exchange_id -> set(uuid)
        self._mem_symbol_open_orders: Dict[str, Set[str]] = defaultdict(set)  # symbol -> set(uuid)
        self._mem_symbol_orders: Dict[str, Set[str]] = defaultdict(set)  # symbol -> set(uuid)
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
        
        self._storage_initialized = False

    ################# # base functions ####################

    def _encode(self, obj: Order | Position | AlgoOrder) -> bytes:
        return msgspec.json.encode(obj)

    def _decode(
        self, data: bytes, obj_type: Type[Order | Position | AlgoOrder]
    ) -> Order | Position | AlgoOrder:
        return msgspec.json.decode(data, type=obj_type)
    
    async def _init_storage(self):
        """Initialize the storage backend"""
        if self._storage_backend == StorageBackend.REDIS:
            self._r_async = RedisClient.get_async_client()
            self._r = RedisClient.get_client()
        elif self._storage_backend == StorageBackend.SQLITE:
            db_path = Path(self._db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._db_async = await aiosqlite.connect(str(db_path))
            self._db = sqlite3.connect(str(db_path))
            await self._init_sqlite_tables()
        self._storage_initialized = True

    async def _init_sqlite_tables(self):
        """Initialize the SQLite tables"""
        async with self._db_async.cursor() as cursor:
            await cursor.executescript("""
                CREATE TABLE IF NOT EXISTS orders (
                    uuid TEXT PRIMARY KEY,
                    strategy_id TEXT,
                    user_id TEXT,
                    symbol TEXT,
                    data BLOB,
                    timestamp INTEGER
                );
                
                CREATE INDEX IF NOT EXISTS idx_orders_symbol 
                ON orders(strategy_id, user_id, symbol);
                
                CREATE TABLE IF NOT EXISTS algo_orders (
                    uuid TEXT PRIMARY KEY,
                    strategy_id TEXT,
                    user_id TEXT,
                    symbol TEXT,
                    data BLOB,
                    timestamp INTEGER
                );
                
                CREATE INDEX IF NOT EXISTS idx_algo_orders_symbol 
                ON algo_orders(strategy_id, user_id, symbol);
                
                CREATE TABLE IF NOT EXISTS positions (
                    symbol TEXT,
                    strategy_id TEXT,
                    user_id TEXT,
                    exchange TEXT,
                    data BLOB,
                    PRIMARY KEY (strategy_id, user_id, symbol)
                );
                
                CREATE TABLE IF NOT EXISTS open_orders (
                    uuid PRIMARY KEY,
                    exchange TEXT,
                    symbol TEXT,
                    strategy_id TEXT,
                    user_id TEXT,
                );
                
                CREATE INDEX IF NOT EXISTS idx_open_orders_uuid 
                ON open_orders(strategy_id, user_id, uuid);
            """)
            await self._db_async.commit()

    async def start(self):
        """Start the cache"""
        await self._init_storage()
        self._task_manager.create_task(self._periodic_sync())

    async def _periodic_sync(self):
        """Periodically sync the cache"""
        while not self._shutdown_event.is_set():
            if self._storage_backend == StorageBackend.REDIS:
                await self._sync_to_redis()
            elif self._storage_backend == StorageBackend.SQLITE:
                await self._sync_to_sqlite()
            self._cleanup_expired_data()
            await asyncio.sleep(self._sync_interval)

    async def _sync_to_redis(self):
        """Sync the cache to Redis"""
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
    
    async def _sync_to_sqlite(self):
        """Sync the cache to SQLite"""
        async with self._db_async.cursor() as cursor:
            # sync orders
            for uuid, order in self._mem_orders.copy().items():
                await cursor.execute(
                    "INSERT OR REPLACE INTO orders (uuid, strategy_id, user_id, symbol, data, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    (uuid, self.strategy_id, self.user_id, order.symbol, self._encode(order), order.timestamp)
                )

            # sync algo orders
            for uuid, algo_order in self._mem_algo_orders.copy().items():
                await cursor.execute(
                    "INSERT OR REPLACE INTO algo_orders (uuid, strategy_id, user_id, symbol, data, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    (uuid, self.strategy_id, self.user_id, algo_order.symbol, self._encode(algo_order), algo_order.timestamp)
                )

            # sync positions
            for symbol, position in self._mem_positions.copy().items():
                await cursor.execute(
                    "INSERT OR REPLACE INTO positions (symbol, strategy_id, user_id, exchange, data) VALUES (?, ?, ?, ?, ?)",
                    (symbol, self.strategy_id, self.user_id, position.exchange.value, self._encode(position))
                )

            # sync open orders
            await cursor.execute("DELETE FROM open_orders WHERE strategy_id = ? AND user_id = ?",
                               (self.strategy_id, self.user_id))
            
            for exchange, uuids in self._mem_open_orders.copy().items():
                for uuid in uuids:
                    order = self._mem_orders.get(uuid)
                    if order:
                        await cursor.execute(
                            "INSERT INTO open_orders (uuid, exchange, symbol, strategy_id, user_id) VALUES (?, ?, ?, ?, ?)",
                            (uuid, exchange.value, order.symbol, self.strategy_id, self.user_id)
                        )

            await self._db_async.commit()

    def _cleanup_expired_data(self):
        """Cleanup expired data"""
        current_time = self._clock.timestamp_ms()
        expire_before = current_time - self._expire_time * 1000

        # Clean up expired orders
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
        """关闭缓存"""
        self._shutdown_event.set()
        if self._storage_initialized:
            if self._storage_backend == StorageBackend.REDIS:
                await self._sync_to_redis()
                await self._r_async.aclose()
            elif self._storage_backend == StorageBackend.SQLITE:
                await self._sync_to_sqlite()
                await self._db_async.close()
                self._db.close()

    ################ # cache public data  ###################

    def _update_kline_cache(self, kline: Kline):
        key = f"{kline.symbol}-{kline.interval.value}"
        self._kline_cache[key] = kline

    def _update_bookl1_cache(self, bookl1: BookL1):
        self._bookl1_cache[bookl1.symbol] = bookl1

    def _update_trade_cache(self, trade: Trade):
        self._trade_cache[trade.symbol] = trade

    def kline(self, symbol: str, interval: KlineInterval) -> Optional[Kline]:
        """
        Retrieve a Kline object from the cache by symbol.

        :param symbol: The symbol of the Kline to retrieve.
        :return: The Kline object if found, otherwise None.
        """
        key = f"{symbol}-{interval.value}"
        return self._kline_cache.get(key, None)

    def bookl1(self, symbol: str) -> Optional[BookL1]:
        """
        Retrieve a BookL1 object from the cache by symbol.

        :param symbol: The symbol of the BookL1 to retrieve.
        :return: The BookL1 object if found, otherwise None.
        """
        return self._bookl1_cache.get(symbol, None)

    def trade(self, symbol: str) -> Optional[Trade]:
        """
        Retrieve a Trade object from the cache by symbol.

        :param symbol: The symbol of the Trade to retrieve.
        :return: The Trade object if found, otherwise None.
        """
        return self._trade_cache.get(symbol, None)

    ################ # cache private data  ###################

    def _check_status_transition(self, order: Order):
        previous_order = self._mem_orders.get(order.uuid)
        if not previous_order:
            return True

        if order.status not in STATUS_TRANSITIONS[previous_order.status]:
            self._log.debug(
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
    
    
    def _get_position_from_redis(self, instrument_id: InstrumentId) -> Position | None:
        key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:exchange:{instrument_id.exchange.value}:symbol_positions:{instrument_id.symbol}"
        if position_data := self._r.get(key):
            position = self._decode(position_data, Position)
            self._mem_positions[instrument_id.symbol] = position  # Cache in memory
            return position
        return None
    
    def _get_position_from_sqlite(self, instrument_id: InstrumentId) -> Position | None:
        try:
            cursor = self._db.cursor()
            cursor.execute(
                """
                SELECT data FROM positions 
                WHERE strategy_id = ? AND user_id = ? AND symbol = ?
                """,
                (
                    self.strategy_id,
                    self.user_id,
                    instrument_id.symbol,
                )
            )
            if row := cursor.fetchone():
                position = self._decode(row[0], Position)
                self._mem_positions[instrument_id.symbol] = position  # Cache in memory
                return position
            return None
        except sqlite3.Error as e:
            self._log.error(f"Error getting position from SQLite: {e}")
            return None
        
    @maybe
    def get_position(self, symbol: str) -> Optional[Position]:
        # First try memory
        instrument_id = InstrumentId.from_str(symbol)
        if position := self._mem_positions.get(symbol, None):
            return position
            
        if self._storage_backend == StorageBackend.REDIS:
            return self._get_position_from_redis(instrument_id)
        elif self._storage_backend == StorageBackend.SQLITE:
            return self._get_position_from_sqlite(instrument_id)
    
    
    def _get_all_positions_from_redis(self, exchange: ExchangeType) -> Dict[str, Position]:
        positions = {}
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

    def _get_all_positions_from_sqlite(self, exchange: ExchangeType) -> Dict[str, Position]:
        positions = {}
        cursor = self._db.cursor()
        cursor.execute(
            """
            SELECT symbol, data FROM positions WHERE strategy_id = ? AND user_id = ? AND exchange = ?
            """,
            (self.strategy_id, self.user_id, exchange.value)
        )
        for row in cursor.fetchall():
            symbol, position_data = row
            if symbol in self._mem_positions:
                continue
            position = self._decode(position_data, Position)
            positions[symbol] = position
            self._mem_positions[symbol] = position  # Cache in memory
        return positions
        
    def get_all_positions(self, exchange: ExchangeType) -> Dict[str, Position]:
        positions = {symbol: position for symbol, position in self._mem_positions.copy().items() if position.exchange == exchange}
        
        if self._storage_backend == StorageBackend.REDIS:
            positions.update(self._get_all_positions_from_redis(exchange))
        elif self._storage_backend == StorageBackend.SQLITE:
            positions.update(self._get_all_positions_from_sqlite(exchange))
        
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

    
    def _get_order_from_redis(self, uuid: str) -> Optional[Order | AlgoOrder]:
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
    
    def _get_order_from_sqlite(self, uuid: str) -> Optional[Order | AlgoOrder]:
        try:
            # determine the table and object type to query
            if uuid.startswith("ALGO-"):
                table = "algo_orders"
                obj_type = AlgoOrder
                mem_dict = self._mem_algo_orders
            else:
                table = "orders"
                obj_type = Order
                mem_dict = self._mem_orders

            # find in memory
            if order := mem_dict.get(uuid):
                return order

            # query SQLite
            cursor = self._db.cursor()
            cursor.execute(
                f"""
                SELECT data FROM {table}
                WHERE uuid = ?
                """,
                (uuid, )
            )
            
            if row := cursor.fetchone():
                order = self._decode(row[0], obj_type)
                mem_dict[uuid] = order  # Cache in memory
                return order
                
            return None
            
        except sqlite3.Error as e:
            self._log.error(f"Error getting order from SQLite: {e}")
            return None
    
    @maybe
    def get_order(self, uuid: str) -> Optional[Order | AlgoOrder]:
        if self._storage_backend == StorageBackend.REDIS:
            return self._get_order_from_redis(uuid)
        elif self._storage_backend == StorageBackend.SQLITE:
            return self._get_order_from_sqlite(uuid)
    
    
    def _get_symbol_orders_from_redis(self, instrument_id: InstrumentId) -> Set[str]:
        key = f"strategy:{self.strategy_id}:user_id:{self.user_id}:exchange:{instrument_id.exchange.value}:symbol_orders:{instrument_id.symbol}"
        if redis_orders := self._r.smembers(key):
            return {uuid.decode() for uuid in redis_orders}
        return set()
    
    def _get_symbol_orders_from_sqlite(self, instrument_id: InstrumentId) -> Set[str]:
        cursor = self._db.cursor()
        cursor.execute(
            """
            SELECT uuid FROM orders WHERE strategy_id = ? AND user_id = ? AND symbol = ?
            """,
            (self.strategy_id, self.user_id, instrument_id.symbol)
        )
        return {row[0] for row in cursor.fetchall()}

    def get_symbol_orders(self, symbol: str, in_mem: bool = True) -> Set[str]:
        """Get all orders for a symbol from memory and Redis"""
        memory_orders = self._mem_symbol_orders.get(symbol, set())
        if not in_mem:
            instrument_id = InstrumentId.from_str(symbol)
            if self._storage_backend == StorageBackend.REDIS:
                orders = self._get_symbol_orders_from_redis(instrument_id)
            elif self._storage_backend == StorageBackend.SQLITE:
                orders = self._get_symbol_orders_from_sqlite(instrument_id)
            return memory_orders.union(orders)
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





