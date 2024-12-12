import asyncio
import platform
from tradebot.engine import TaskManager

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
