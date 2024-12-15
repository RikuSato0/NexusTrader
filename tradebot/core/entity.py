import signal
import asyncio
import socket
from collections import defaultdict
from typing import Callable, Optional
from typing import Dict, List, Any

import time
import redis

from dataclasses import dataclass
from tradebot.constants import get_redis_config
from tradebot.core.log import SpdLog
from tradebot.core.nautilius_core import LiveClock


@dataclass
class RateLimit:
    """
    max_rate: Allow up to max_rate / time_period acquisitions before blocking.
    time_period: Time period in seconds.
    """
    max_rate: float
    time_period: float = 60


class TaskManager:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self._log = SpdLog.get_logger(type(self).__name__, level="DEBUG", flush=True)
        self._tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        self._loop = loop
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        for sig in (signal.SIGINT, signal.SIGTERM):
            self._loop.add_signal_handler(sig, lambda: self.create_task(self._shutdown()))

    async def _shutdown(self):
        self._shutdown_event.set()
        self._log.debug("Shutdown signal received, cleaning up...")

    def create_task(self, coro: asyncio.coroutines) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._tasks.append(task)
        task.add_done_callback(self._handle_task_done)
        return task

    def _handle_task_done(self, task: asyncio.Task):
        try:
            self._tasks.remove(task)
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._log.error(f"Error during task done: {e}")
            raise

    async def wait(self):
        try:
            if self._tasks:
                await self._shutdown_event.wait()
                self._log.debug("Shutdown Completed")
        except Exception as e:
            self._log.error(f"Error during wait: {e}")
            raise

    async def cancel(self):
        try:
            for task in self._tasks:
                if not task.done():
                    task.cancel()

            if self._tasks:
                results = await asyncio.gather(*self._tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, Exception) and not isinstance(
                        result, asyncio.CancelledError
                    ):
                        self._log.error(f"Task failed during cancellation: {result}")

        except Exception as e:
            self._log.error(f"Error during cancellation: {e}")
            raise
        finally:
            self._tasks.clear()


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




class Clock:
    def __init__(self, tick_size: float = 1.0):
        """
        :param tick_size_s: Time interval of each tick in seconds (supports sub-second precision).
        """
        self._tick_size = tick_size  # Tick size in seconds
        self._current_tick = (time.time() // self._tick_size) * self._tick_size
        self._clock = LiveClock()
        self._tick_callbacks: List[Callable[[float], None]] = []
        self._started = False

    @property
    def tick_size(self) -> float:
        return self._tick_size

    @property
    def current_timestamp(self) -> float:
        return self._clock.timestamp()

    def add_tick_callback(self, callback: Callable[[float], None]):
        """
        Register a callback to be called on each tick.
        :param callback: Function to be called with current_tick as argument.
        """
        self._tick_callbacks.append(callback)

    async def run(self):
        if self._started:
            raise RuntimeError("Clock is already running.")
        self._started = True
        while True:
            now = time.time()
            next_tick_time = self._current_tick + self._tick_size
            sleep_duration = next_tick_time - now
            if sleep_duration > 0:
                await asyncio.sleep(sleep_duration)
            else:
                # If we're behind schedule, skip to the next tick to prevent drift
                next_tick_time = now
            self._current_tick = next_tick_time
            for callback in self._tick_callbacks:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self.current_timestamp)
                else:
                    callback(self.current_timestamp)

class ZeroMQSignalRecv:
    def __init__(self, config, callback: Callable, task_manager: TaskManager):
        self._socket = config.socket
        self._callback = callback
        self._task_manager = task_manager
    
    async def _recv(self):
        while True:
            date = await self._socket.recv()
            if asyncio.iscoroutinefunction(self._callback):
                await self._callback(date)
            else:
                self._callback(date)
                
    async def start(self):
        self._task_manager.create_task(self._recv())
                