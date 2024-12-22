import pytest
import time
from copy import copy
from tradebot.schema import Order, ExchangeType, BookL1, Kline, Trade, Position
from tradebot.constants import OrderStatus, OrderSide, OrderType
from tradebot.core.cache import AsyncCache


@pytest.fixture
def async_cache(task_manager, message_bus) -> AsyncCache:
    from tradebot.core.cache import AsyncCache

    cache = AsyncCache(
        strategy_id="test-strategy",
        user_id="test-user",
        msgbus=message_bus,
        task_manager=task_manager,
    )
    return cache


@pytest.fixture
def sample_order():
    return Order(
        id="test-order-1",
        uuid="test-uuid-1",
        exchange=ExchangeType.BINANCE,
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        status=OrderStatus.PENDING,
        price=50000.0,
        amount=1.0,
        timestamp=1000,
    )


################ # test cache public data  ###################


async def test_market_data_cache(async_cache: AsyncCache):
    # Test kline update

    kline = Kline(
        symbol="BTC/USDT",
        exchange=ExchangeType.BINANCE,
        timestamp=1000,
        open=50000.0,
        high=51000.0,
        low=49000.0,
        close=50500.0,
        volume=100.0,
        interval="1m",
    )
    async_cache._update_kline_cache(kline)
    assert async_cache.kline("BTC/USDT") == kline

    # Test bookL1 update
    bookl1 = BookL1(
        symbol="BTC/USDT",
        exchange=ExchangeType.BINANCE,
        timestamp=1000,
        bid=50000.0,
        ask=50100.0,
        bid_size=1.0,
        ask_size=1.0,
    )
    async_cache._update_bookl1_cache(bookl1)
    assert async_cache.bookl1("BTC/USDT") == bookl1


################ # test cache private data  ###################


async def test_order_management(async_cache: AsyncCache, sample_order: Order):
    # Test order initialization
    sample_order.timestamp = time.time()
    async_cache._order_initialized(sample_order)
    assert async_cache.get_order(sample_order.uuid) == sample_order
    assert sample_order.uuid in async_cache.get_open_orders(symbol=sample_order.symbol)
    assert sample_order.uuid in async_cache.get_symbol_orders(sample_order.symbol)

    # Test order status update
    updated_order: Order = copy(sample_order)
    updated_order.status = OrderStatus.FILLED
    async_cache._order_status_update(updated_order)

    assert async_cache.get_order(updated_order.uuid) == updated_order
    assert updated_order.uuid not in async_cache.get_open_orders(
        symbol=updated_order.symbol
    )


async def test_cache_cleanup(async_cache: AsyncCache, sample_order: Order):
    sample_order.timestamp = time.time() * 1000
    async_cache._order_initialized(sample_order)
    async_cache._cleanup_expired_data()

    # Order should still exist as it's not expired
    assert async_cache.get_order(sample_order.uuid) is not None

    # Create expired order
    expired_order: Order = copy(sample_order)
    expired_order.uuid = "expired-uuid"
    expired_order.timestamp = 1  # Very old timestamp

    async_cache._order_initialized(expired_order)
    async_cache._cleanup_expired_data()

    # Expired order should be removed
    assert async_cache.get_order(expired_order.uuid) is None


@pytest.fixture
def position_order():
    return Order(
        id="test-order-1",
        uuid="test-uuid-1",
        exchange=ExchangeType.BINANCE,
        symbol="BTCUSDT.BINANCE",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        status=OrderStatus.PENDING,
        price=50000.0,
        amount=1.0,
        timestamp=1000,
    )


@pytest.fixture
def filled_order(position_order: Order) -> Order:
    filled = copy(position_order)
    filled.status = OrderStatus.FILLED
    filled.filled = filled.amount
    return filled


async def test_apply_position(async_cache: AsyncCache, filled_order: Order):
    # Test position creation and update with filled order
    async_cache._apply_position(filled_order)

    position: Position = async_cache.get_position(filled_order.symbol)
    assert position is not None
    assert position.symbol == filled_order.symbol
    assert position.exchange == filled_order.exchange
    # For a BUY order, position size should be positive
    assert position.amount == filled_order.filled

    # Test with SELL order
    sell_order = copy(filled_order)
    sell_order.uuid = "test-uuid-2"
    sell_order.side = OrderSide.SELL
    async_cache._apply_position(sell_order)

    position = async_cache.get_position(sell_order.symbol)
    # After buying and selling same amount, position should be zero
    assert position.amount == 0


@pytest.fixture
def position():
    return Position(
        symbol="BTC/USDT",
        exchange=ExchangeType.BINANCE,
        strategy_id="test-strategy",
    )


async def test_get_position(async_cache: AsyncCache, position: Position):
    # Test getting non-existent position
    assert async_cache.get_position("NON/EXISTENT") is None

    # Test getting position after applying order
    symbol = "BTC/USDT"
    async_cache._mem_symbol_positions[symbol] = position

    retrieved_position = async_cache.get_position(symbol)
    assert retrieved_position is not None
    assert retrieved_position.symbol == symbol
    assert retrieved_position.exchange == ExchangeType.BINANCE
    assert retrieved_position.strategy_id == "test-strategy"


async def test_apply_position_with_closed_orders(
    async_cache: AsyncCache, filled_order: Order
):
    # First application should update position
    async_cache._apply_position(filled_order)
    initial_position = async_cache.get_position(filled_order.symbol)
    initial_size = initial_position.size

    # Second application of same order should not affect position
    async_cache._apply_position(filled_order)
    position = async_cache.get_position(filled_order.symbol)
    assert position.size == initial_size
    assert async_cache._mem_closed_orders.get(filled_order.uuid) is True
