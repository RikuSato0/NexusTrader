import pytest
import asyncio
from nexustrader.core.entity import TaskManager
from nexustrader.core.nautilius_core import MessageBus, LiveClock
from nexustrader.core.registry import OrderRegistry
from nautilus_trader.model.identifiers import TraderId

import pytest

from decimal import Decimal
from nexustrader.schema import Order, ExchangeType
from nexustrader.constants import OrderStatus, OrderSide, OrderType, PositionSide


"""
Creates one fixture for the entire test run
Most efficient but least isolated
Example: Database connection that can be reused across all tests
"""


@pytest.fixture(scope="session")
def event_loop_policy():
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def task_manager(event_loop_policy):
    loop = event_loop_policy.new_event_loop()
    return TaskManager(loop, enable_signal_handlers=False)


@pytest.fixture
def message_bus():
    return MessageBus(trader_id=TraderId("TEST-001"), clock=LiveClock())


@pytest.fixture
def order_registry():
    return OrderRegistry()


def create_position_orders():
    # Long position orders
    long_open_order = Order(
        exchange=ExchangeType.BINANCE,
        symbol="BTCUSDT.BINANCE",
        status=OrderStatus.FILLED,
        id="123",
        uuid="uuid-123",
        amount=Decimal("1.0"),
        filled=Decimal("1.0"),
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        price=50000.0,
        average=50000.0,
        remaining=Decimal("0"),
        position_side=PositionSide.FLAT,
    )

    long_close_order = Order(
        exchange=ExchangeType.BINANCE,
        symbol="BTCUSDT.BINANCE",
        status=OrderStatus.FILLED,
        id="124",
        uuid="uuid-124",
        amount=Decimal("1.0"),
        filled=Decimal("1.0"),
        type=OrderType.LIMIT,
        side=OrderSide.SELL,
        price=51000.0,
        average=51000.0,
        remaining=Decimal("0"),
        position_side=PositionSide.FLAT,
    )

    # Short position orders
    short_open_order = Order(
        exchange=ExchangeType.BINANCE,
        symbol="BTCUSDT.BINANCE",
        status=OrderStatus.FILLED,
        id="125",
        uuid="uuid-125",
        amount=Decimal("1.0"),
        filled=Decimal("1.0"),
        type=OrderType.LIMIT,
        side=OrderSide.SELL,
        price=52000.0,
        average=52000.0,
        remaining=Decimal("0"),
        position_side=PositionSide.FLAT,
    )

    short_close_order = Order(
        exchange=ExchangeType.BINANCE,
        symbol="BTCUSDT.BINANCE",
        status=OrderStatus.FILLED,
        id="126",
        uuid="uuid-126",
        amount=Decimal("1.0"),
        filled=Decimal("1.0"),
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        price=51500.0,
        average=51500.0,
        remaining=Decimal("0"),
        position_side=PositionSide.FLAT,
    )

    # Partially filled order
    partial_order = Order(
        exchange=ExchangeType.BINANCE,
        symbol="BTCUSDT.BINANCE",
        status=OrderStatus.PARTIALLY_FILLED,
        id="127",
        uuid="uuid-127",
        amount=Decimal("2.0"),
        filled=Decimal("1.0"),
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        price=50000.0,
        average=50000.0,
        remaining=Decimal("1.0"),
        position_side=PositionSide.FLAT,
    )

    return {
        "long_open": long_open_order,
        "long_close": long_close_order,
        "short_open": short_open_order,
        "short_close": short_close_order,
        "partial": partial_order,
    }
