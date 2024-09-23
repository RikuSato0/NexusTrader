import asyncio


import ccxt.pro as ccxtpro


from abc import ABC, abstractmethod
from typing import Dict, List, Any
from typing import Callable, Literal
from collections import defaultdict
from decimal import Decimal

from tradebot.entity import log_register
from tradebot.entity import OrderResponse
from tradebot.exceptions import OrderResponseError

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
    def __init__(self, exchange: ExchangeManager):
        self._exchange = exchange
    
    async def place_limit_order(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        amount: Decimal,
        price: Decimal,
        close_position: bool = False,
        **params,
    ):
        try:
            if close_position:
                params["reduceOnly"] = True
            res = await self._exchange.api.create_order(
                symbol=symbol,
                type="limit",
                side=side,
                amount=amount,
                price=price,
                params=params,
            )
            return OrderResponse(**res)
        except Exception as e:
            raise OrderResponseError(e, {"symbol": symbol, "side": side, "amount": amount, "price": price, **params})
            
        
    
    async def place_limit_order_ws(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        amount: Decimal,
        price: Decimal,
        close_position: bool = False,
        **params,
    ):
        try:
            if close_position:
                params["reduceOnly"] = True
            res = await self._exchange.api.create_order_ws(
                symbol=symbol,
                type="limit",
                side=side,
                amount=amount,
                price=price,
                params=params,
            )
            return OrderResponse(**res)
        except Exception as e:
            raise OrderResponseError(e, {"symbol": symbol, "side": side, "amount": amount, "price": price, **params})
    
    async def place_market_order(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        amount: Decimal,
        close_position: bool = False,
        **params,
    ):
        try:
            if close_position:
                params["reduceOnly"] = True
            res = await self._exchange.api.create_order(
                symbol=symbol,
                type="market",
                side=side,
                amount=amount,
                params=params,
            )
            return OrderResponse(**res)
        except Exception as e:
            raise OrderResponseError(e, {"symbol": symbol, "side": side, "amount": amount, **params})
    
    async def place_market_order_ws(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        amount: Decimal,
        close_position: bool = False,
        **kwargs,
    ):
        try:
            if close_position:
                kwargs["reduceOnly"] = True
            res = await self._exchange.api.create_order_ws(
                symbol=symbol,
                type="market",
                side=side,
                amount=amount,
                params=kwargs,
            )
            return OrderResponse(**res)
        except Exception as e:
            raise OrderResponseError(e, {"symbol": symbol, "side": side, "amount": amount, **kwargs})
    
    async def cancel_order(self, id: str, symbol: str,  **params):
        try:
            res = await self._exchange.api.cancel_order(id, symbol, params=params)
            return OrderResponse(**res)
        except Exception as e:
            raise OrderResponseError(e, {"id": id, "symbol": symbol, **params})
    
    async def cancel_order_ws(self, order_id: str, **params):
        try:
            res = await self._exchange.api.cancel_order_ws(order_id, params=params)
            return OrderResponse(**res)
        except Exception as e:
            raise OrderResponseError(e, {"order_id": order_id, **params})


class WebsocketManager(ABC):
    def __init__(
        self,
        base_url: str,
        ping_interval: int = 5,
        ping_timeout: int = 5,
        close_timeout: int = 1,
        max_queue: int = 12,
    ):
        self._base_url = base_url
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout
        self._close_timeout = close_timeout
        self._max_queue = max_queue
        
        self._tasks: List[asyncio.Task] = []
        self._subscripions = defaultdict(asyncio.Queue)
        self._log = log_register.get_logger(name=type(self).__name__, level="INFO", flush=True)
        
    async def _consume(self, subscription_id: str, callback: Callable[..., Any] = None, *args, **kwargs):
        while True:
            msg = await self._subscripions[subscription_id].get()
            if asyncio.iscoroutinefunction(callback):
                await callback(msg, *args, **kwargs)
            else:
                callback(msg, *args, **kwargs)
            self._subscripions[subscription_id].task_done()

    @abstractmethod
    async def _subscribe(self, symbol: str, typ: str, channel: str, queue_id: str):
        pass


    async def close(self):
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._log.info("All WebSocket connections closed.")
    
    
