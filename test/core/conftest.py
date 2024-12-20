import pytest
import asyncio
from tradebot.core.entity import TaskManager
from tradebot.core.nautilius_core import MessageBus, LiveClock
from tradebot.core.registry import OrderRegistry


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
    return TaskManager(event_loop_policy)


@pytest.fixture
def message_bus():
    return MessageBus(trader_id="TEST-001", clock=LiveClock())


@pytest.fixture
def order_registry():
    return OrderRegistry()
