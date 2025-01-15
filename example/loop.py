import asyncio
import platform
from tradebot.core.log import SpdLog
from typing import List
import signal

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
        self._log.info("Shutdown signal received, cleaning up...")
        self._shutdown_event.set()

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
            await self._shutdown_event.wait()
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
            
class Loop1:
    def __init__(self, task_manager: TaskManager):
        self._task_manager = task_manager

    async def _task1(self):
        while True:
            print("task1")
            await asyncio.sleep(5)
            raise Exception("task1 error")

    async def run(self):
        self._task_manager.create_task(self._task1())


class Loop2:
    def __init__(self, task_manager: TaskManager):
        self._task_manager = task_manager

    async def _task2(self):
        while True:
            print("task2")
            await asyncio.sleep(1)

    async def run(self):
        self._task_manager.create_task(self._task2())


class Engine:
    @staticmethod
    def set_loop_policy():
        if platform.system() != 'Windows':
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    def __init__(self):
        self.set_loop_policy()  
        self._loop = asyncio.new_event_loop()
        self._task_manager = TaskManager(self._loop)
        self._loop1 = Loop1(self._task_manager)
        self._loop2 = Loop2(self._task_manager)
    
    async def _run(self):
        await self._loop1.run()
        await self._loop2.run()
        await self._task_manager.wait()
    
    async def _dispose(self):
        await self._task_manager.cancel()
        

    def run(self):
        self._loop.run_until_complete(self._run())

    def dispose(self):
        self._loop.run_until_complete(self._dispose())
        self._loop.close()


def main():
    try:
        engine = Engine()
        engine.run()
    finally:
        engine.dispose()


if __name__ == "__main__":

    main()
