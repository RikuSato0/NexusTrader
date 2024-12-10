import asyncio
import signal
import uvloop
from typing import List

from tradebot.base import PublicConnector, PrivateConnector
from tradebot.core import Strategy


class Engine:
    def __init__(self, config: dict):
        self.config = config
        self._public_connectors: List[PublicConnector] = []
        self._private_connectors: List[PrivateConnector] = []
        self._strategies: List[Strategy] = []
        self._is_running = False
        self._is_built = False
        self.loop = asyncio.get_event_loop()

    def add_connector(self, connector: PublicConnector | PrivateConnector):
        self.connectors.append(connector)

    def add_strategy(self, strategy: Strategy):
        self.strategies.append(strategy)

    def build(self):
        if self._is_built:
            raise RuntimeError("The engine is already built.")
        
        self._is_built = True

    def start(self):
        if not self._is_built:
            raise RuntimeError("The engine is not built. Call `build()` first.")
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        self.loop = asyncio.get_event_loop()
        self._is_running = True
        self.loop.run_until_complete(self.run_async())

    async def run_async(self):
        try:
            tasks = [connector.connect() for connector in self.connectors]
            tasks += [strategy.run() for strategy in self.strategies]
            await asyncio.gather(*tasks)
        except asyncio.CancelledError as e:
            print(f"Cancelled: {e}")

    def stop(self):
        self._is_running = False
        for connector in self.connectors:
            connector.stop()
        self.loop.stop()

    def dispose(self):
        if self.loop.is_running():
            print("Cannot close a running event loop")
        else:
            print("Closing event loop")
            self.loop.close()

    def _loop_sig_handler(self, sig: signal.Signals):
        print(f"Received {sig.name}, shutting down")
        self.stop()
