import asyncio


import ccxt.pro as ccxtpro


from abc import ABC, abstractmethod
from typing import Dict, List, Any
from typing import Callable


from tradebot.entity import log_register


class ExchangeManager(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api = self._init_exchange()
        self.market = None
    
    def _init_exchange(self) -> ccxtpro.Exchange:
        try:
            exchange_class = getattr(ccxtpro, self.config["exchange_id"])
        except AttributeError:
            raise AttributeError(f"Exchange {self.config['exchange_id']} is not supported")
        
        api = exchange_class(self.config)
        api.set_sandbox_mode(self.config.get("sandbox", False)) # Set sandbox mode if demo trade is enabled
        
        return api
    
    async def load_markets(self):
        self.market = await self.api.load_markets()
        return self.market

    async def close(self):
        await self.api.close()
    
        
class AccountManager(ABC):
    pass


class OrderManager(ABC):
    pass


class WebsocketManager(ABC):
    def __init__(self, config: Dict[str, Any] = None, ping_interval: int = 5, ping_timeout: int = 5, close_timeout: int = 1, max_queue: int = 12):
        self.queues: Dict[str, asyncio.Queue] = {}
        self.tasks: List[asyncio.Task] = []
        
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.close_timeout = close_timeout
        self.max_queue = max_queue
        
        if config:
            self.api_key = config.get("apiKey", None)
            self.secret = config.get("secret", None)
            self.password = config.get("password", None)
        
        self.logger = log_register.get_logger(self.__class__.__name__, level="INFO", flush=True)
        
    async def consume(self, queue_id: str, callback: Callable[..., Any] = None, *args, **kwargs):
        while True:
            msg = await self.queues[queue_id].get()
            if asyncio.iscoroutinefunction(callback):
                await callback(msg, *args, **kwargs)
            else:
                callback(msg, *args, **kwargs)
            self.queues[queue_id].task_done()

    @abstractmethod
    async def _subscribe(self, symbol: str, typ: str, channel: str, queue_id: str):
        pass

    async def subscribe(self, symbols: List[str], typ: str, channel: str, callback: Callable[[Dict[str, Any]], None] = None, *args, **kwargs):
        for symbol in symbols:
            queue_id = f"{symbol}_{typ}_{channel}"
            self.queues[queue_id] = asyncio.Queue()
            self.tasks.append(asyncio.create_task(self.consume(queue_id, callback, *args, **kwargs)))
            self.tasks.append(asyncio.create_task(self._subscribe(symbol, typ, channel, queue_id)))

    async def close(self):
        self.logger.info("Shutting down WebSocket connections...")
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.logger.info("All WebSocket connections closed.")
    
    
