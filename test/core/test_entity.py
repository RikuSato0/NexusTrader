import pytest
import asyncio
from tradebot.core.entity import TaskManager, EventSystem


@pytest.mark.asyncio
async def test_task_creation_and_execution(task_manager: TaskManager) -> None:
    result = []

    async def sample_task():
        await asyncio.sleep(0.1)
        result.append(1)

    task = task_manager.create_task(sample_task())
    await task

    assert result == [1]
    assert not task_manager._tasks  # Task should be removed after completion


@pytest.mark.asyncio
async def test_task_cancellation(task_manager: TaskManager) -> None:
    async def long_running_task():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            return "cancelled"

    task = task_manager.create_task(long_running_task())
    await asyncio.sleep(0.1)
    await task_manager.cancel()

    assert not task_manager._tasks
    assert task.cancelled()


# def test_event_system():
#     results = []

#     @EventSystem.on("test_event")
#     def handler(data):
#         results.append(data)

#     EventSystem.emit("test_event", "test_data")
#     assert results == ["test_data"]


# @pytest.mark.asyncio
# async def test_event_system_async():
#     results = []

#     @EventSystem.on("test_event")
#     async def async_handler(data):
#         results.append(data)

#     await EventSystem.aemit("test_event", "test_data")
#     assert results == ["test_data"]
