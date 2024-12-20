import pytest
from tradebot.schema import Order, ExchangeType, BookL1, Kline, Trade
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
    )
    async_cache._update_kline_cache(kline)
    assert async_cache.kline("BTC/USDT") == kline

    # Test bookL1 update
    bookl1 = BookL1(
        symbol="BTC/USDT",
        exchange=ExchangeType.BINANCE,
        timestamp=1000,
        bid_price=50000.0,
        bid_volume=1.0,
        ask_price=50100.0,
        ask_volume=1.0,
    )
    async_cache._update_bookl1_cache(bookl1)
    assert async_cache.bookl1("BTC/USDT") == bookl1


async def test_order_management(async_cache: AsyncCache, sample_order: Order):
    # Test order initialization
    async_cache._order_initialized(sample_order)
    assert async_cache.get_order(sample_order.uuid) == sample_order
    assert sample_order.uuid in async_cache.get_open_orders(symbol=sample_order.symbol)

    # Test order status update
    updated_order: Order = sample_order.copy()
    updated_order.status = OrderStatus.FILLED
    async_cache._order_status_update(updated_order)

    assert async_cache.get_order(updated_order.uuid) == updated_order
    assert updated_order.uuid not in async_cache.get_open_orders(
        symbol=updated_order.symbol
    )


async def test_cache_cleanup(async_cache: AsyncCache, sample_order: Order):
    async_cache._order_initialized(sample_order)
    async_cache._cleanup_expired_data()

    # Order should still exist as it's not expired
    assert async_cache.get_order(sample_order.uuid) is not None

    # Create expired order
    expired_order: Order = sample_order.copy()
    expired_order.uuid = "expired-uuid"
    expired_order.timestamp = 0  # Very old timestamp

    async_cache._order_initialized(expired_order)
    async_cache._cleanup_expired_data()

    # Expired order should be removed
    assert async_cache.get_order(expired_order.uuid) is None
