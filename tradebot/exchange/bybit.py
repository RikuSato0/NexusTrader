import base64
from decimal import Decimal
import hmac
import json
import time

import requests
import asyncio
import aiohttp


from collections import defaultdict
from typing import Any, Dict, List
from typing import Literal, Callable, Awaitable


import orjson
import aiohttp
import websockets
import ccxt.pro as ccxtpro


from asynciolimiter import Limiter
from websockets.asyncio.connection import Connection

from tradebot.constants import IntervalType, UrlType
from tradebot.entity import EventSystem
from tradebot.base import ExchangeManager, OrderManager, AccountManager, WebsocketManager



class CustomConnection(Connection):
    async def ping(self, data: bytes | None = None) -> Awaitable[float]:
        ping_message = json.dumps({"op": "ping"})
        self.send(ping_message)
        return await super().ping(data)
    
class BybitWebsocketManager(WebsocketManager):
    def __init__(self, url: UrlType, api_key: str = None, secret: str = None, testnet: bool = False):
        base_url = url.TESTNET if testnet else url.MAINNET
        super().__init__(
            base_url=base_url,
            ping_interval=5,
            ping_timeout=5,
            close_timeout=1,
            max_queue=12,
        )
        self._api_key = api_key
        self._secret = secret
    
    async def _subscribe(self, payload: Dict[str, Any], subscription_id: str):
        async for websocket in websockets.connect(
            uri = self._base_url,
            ping_interval=self._ping_interval,
            ping_timeout=self._ping_timeout,
            close_timeout=self._close_timeout,
            max_queue=self._max_queue,
            # create_connection = CustomConnection,
        ):
            try:
                payload = json.dumps(payload)
                await websocket.send(payload)
                async for msg in websocket:
                    msg = orjson.loads(msg)
                    await self._subscripions[subscription_id].put(msg)
            except websockets.ConnectionClosed:
                self._log.error(f"Connection closed, reconnecting...")
    
    async def subscribe_orderbook(self, symbol: str, depth: int = 1, callback: Callable[..., Any] = None, *args, **kwargs):
        subscription_id = f"orderbook.{depth}.{symbol}"
        
        payload = {
            "op": "subscribe",
            "args": [subscription_id]
        }
        
        if subscription_id not in self._subscripions:
            self._tasks.append(asyncio.create_task(self._consume(subscription_id, callback=callback, *args, **kwargs)))
            self._tasks.append(asyncio.create_task(self._subscribe(payload, subscription_id)))
        else:
            self._log.info(f"Already subscribed to {subscription_id}")



class BybitExchangeManager(ExchangeManager):
    pass

class BybitOrderManager(OrderManager):
    pass

class BybitAccountManager(AccountManager):
    pass


