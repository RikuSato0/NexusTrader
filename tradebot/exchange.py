import base64
import hmac
import json
import time

import requests
import asyncio


from collections import defaultdict
from typing import Any, Dict, List
from typing import Literal, Callable


import orjson
import aiohttp
import websockets


from asynciolimiter import Limiter
from websockets.asyncio import client


from tradebot.constants import MARKET_URLS
from tradebot.entity import log_register
from tradebot.entity import EventSystem
from tradebot.base import ExchangeManager, OrderManager, AccountManager, WebsocketManager



class BybitExchangeManager(ExchangeManager):
    pass

class BybitOrderManager(OrderManager):
    pass

class BybitAccountManager(AccountManager):
    pass

class BybitWebsocketManager:
    pass




class BinanceExchangeManager(ExchangeManager):
    pass

class BinanceOrderManager(OrderManager):
    pass

class BinanceAccountManager(AccountManager):
    pass

class BinanceWebsocketManager(WebsocketManager):
    def __init__(self, base_url: str):
        super().__init__(
            base_url=base_url,
            ping_interval=5,
            ping_timeout=5,
            close_timeout=1,
            max_queue=12,
        )
    
    async def _subscribe(self, payload: Dict[str, Any], subscription_id: str):
        async for websocket in websockets.connect(
            uri = self._base_url,
            ping_interval=self._ping_interval,
            ping_timeout=self._ping_timeout,
            close_timeout=self._close_timeout,
            max_queue=self._max_queue,
        ):
            try:
                payload = json.dumps(payload)
                await websocket.send(payload)
                async for msg in websocket:
                    msg = orjson.loads(msg)
                    await self._subscripions[subscription_id].put(msg)
            except websockets.ConnectionClosed:
                self._log.error(f"Connection closed, reconnecting...")
    
    async def subscribe_book_ticker(self, symbol: str, callback: Callable[..., Any] = None, *args, **kwargs):
        subscription_id = f"book_ticker.{symbol}"
        id = int(time.time() * 1000)
        payload = {
            "method": "SUBSCRIBE",
            "params": [f"{symbol.lower()}@bookTicker"],
            "id": id
        }
        if subscription_id not in self._subscripions:
            self._tasks.append(asyncio.create_task(self._consume(subscription_id, callback=callback, *args, **kwargs)))
            self._tasks.append(asyncio.create_task(self._subscribe(payload, subscription_id)))
        else:
            self._log.info(f"Already subscribed to {subscription_id}")
    
    async def subscribe_book_tickers(self, symbols: List[str], callback: Callable[..., Any] = None, *args, **kwargs):
        for symbol in symbols:
            await self.subscribe_book_ticker(symbol, callback=callback, *args, **kwargs)
        
    async def subscribe_trade(self, symbol: str, callback: Callable[..., Any] = None, *args, **kwargs):
        subscription_id = f"trade.{symbol}"
        id = int(time.time() * 1000)
        payload = {
            "method": "SUBSCRIBE",
            "params": [f"{symbol.lower()}@trade"],
            "id": id
        }
        if subscription_id not in self._subscripions: 
            self._tasks.append(asyncio.create_task(self._consume(subscription_id, callback=callback, *args, **kwargs)))
            self._tasks.append(asyncio.create_task(self._subscribe(payload, subscription_id)))
        else:
            self._log.info(f"Already subscribed to {subscription_id}")
    
    
    async def subscribe_trades(self, symbols: List[str], callback: Callable[..., Any] = None, *args, **kwargs):
        for symbol in symbols:
            await self.subscribe_trade(symbol, callback=callback, *args, **kwargs)
    
    async def subscribe_agg_trade(self, symbol: str, callback: Callable[..., Any] = None, *args, **kwargs):
        subscription_id = f"agg_trade.{symbol}"
        id = int(time.time() * 1000)
        payload = {
            "method": "SUBSCRIBE",
            "params": [f"{symbol.lower()}@aggTrade"],
            "id": id
        }
        if subscription_id not in self._subscripions:
            self._tasks.append(asyncio.create_task(self._consume(subscription_id, callback=callback, *args, **kwargs)))
            self._tasks.append(asyncio.create_task(self._subscribe(payload, subscription_id)))
        else:
            self._log.info(f"Already subscribed to {subscription_id}")  
    
    async def subscribe_agg_trades(self, symbols: List[str], callback: Callable[..., Any] = None, *args, **kwargs):
        for symbol in symbols:
            await self.subscribe_agg_trade(symbol, callback=callback, *args, **kwargs)





class OkxExchangeManager(ExchangeManager):
    pass

class OkxOrderManager(OrderManager):
    pass

class OkxAccountManager(AccountManager):
    pass

class OkxWebsocketManager(WebsocketManager):
    def __init__(self, base_url: str, api_key: str = None, secret: str = None, passphrase: str = None):
        super().__init__(
            base_url=base_url,
            ping_interval=5,
            ping_timeout=5,
            close_timeout=1,
            max_queue=12,
        )
        
        self._api_key = api_key
        self._secret = secret
        self._passphrase = passphrase
        
        
    async def _subscribe(self, payload: Dict[str, Any], subscription_id: str, auth: bool = False):
        if auth:
            self._base_url = f"{self._base_url}/v5/private"
        else:
            self._base_url = f"{self._base_url}/v5/public"
            
        async for websocket in websockets.connect(
            uri = self._base_url,
            ping_interval=self._ping_interval,
            ping_timeout=self._ping_timeout,
            close_timeout=self._close_timeout,
            max_queue=self._max_queue,
        ):
            try:
                if auth:
                    auth_payload = self._get_auth_payload()
                    await websocket.send(auth_payload)
                    await asyncio.sleep(5)
                payload = json.dumps(payload)
                await websocket.send(payload)
                async for msg in websocket:
                    msg = orjson.loads(msg)
                    await self._subscripions[subscription_id].put(msg)
            except websockets.ConnectionClosed:
                self._log.error(f"Connection closed, reconnecting...")

    def _get_auth_payload(self):
        timestamp = int(time.time())
        message = str(timestamp) + 'GET' + '/users/self/verify'
        mac = hmac.new(bytes(self._secret, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
        d = mac.digest()
        sign = base64.b64encode(d)
        if self._api_key is None or self._passphrase is None or self._secret is None:
            raise ValueError("API Key, Passphrase, or Secret is missing.")
        arg = {"apiKey": self._api_key, "passphrase": self._passphrase, "timestamp": timestamp, "sign": sign.decode("utf-8")}
        payload = {"op": "login", "args": [arg]}
        return json.dumps(payload)

    async def _consume(self, subscription_id: str, callback: Callable[..., Any] = None, *args, **kwargs):
        while True:
            msg = await self._subscripions[subscription_id].get()
            if asyncio.iscoroutinefunction(callback):
                await callback(msg, *args, **kwargs)
            else:
                callback(msg, *args, **kwargs)
            self._subscripions[subscription_id].task_done()
    
    async def subscribe_order_book(self, symbol: str, channel: Literal["books", "books5", "bbo-tbt", "books-l2-tbt", "books50-l2-tbt"], callback: Callable[..., Any] = None, *args, **kwargs):
        subscription_id = f"{channel}.{symbol}"
        payload = {
            "op": "subscribe",
            "args": [{
                "channel": channel,
                "instId": symbol
            }]
        }
        if subscription_id not in self._subscripions:
            self._tasks.append(asyncio.create_task(self._consume(subscription_id, callback=callback, *args, **kwargs)))
            self._tasks.append(asyncio.create_task(self._subscribe(payload, subscription_id)))
        else:
            self._log.info(f"Already subscribed to {subscription_id}")
    
    async def subscribe_trade(self, symbol: str, callback: Callable[..., Any] = None, *args, **kwargs):
        subscription_id = f"trades.{symbol}"
        payload = {
            "op": "subscribe",
            "args": [{
                "channel": "trades",
                "instId": symbol
            }]
        }
        if subscription_id not in self._subscripions:
            self._tasks.append(asyncio.create_task(self._consume(subscription_id, callback=callback, *args, **kwargs)))
            self._tasks.append(asyncio.create_task(self._subscribe(payload, subscription_id)))
        else:
            self._log.info(f"Already subscribed to {subscription_id}")
            
    async def subscribe_account(self, callback: Callable[..., Any] = None, *args, **kwargs):
        subscription_id = "account"
        payload = {
            "op": "subscribe",
            "args": [{
                "channel": "account"
            }]
        }
        if subscription_id not in self._subscripions:
            self._tasks.append(asyncio.create_task(self._consume(subscription_id, callback=callback, *args, **kwargs)))
            self._tasks.append(asyncio.create_task(self._subscribe(payload, subscription_id, auth=True)))
        else:
            self._log.info(f"Already subscribed to {subscription_id}")
    
    async def subscribe_position(self, inst_type:Literal["MARGIN", "SWAP", "FUTURES", "OPTION", "ANY"] = "ANY", callback: Callable[..., Any] = None, *args, **kwargs):
        subscription_id = "position"
        payload = {
            "op": "subscribe",
            "args": [{
                "channel": "positions",
                "instType": inst_type
            }]
        }
        if subscription_id not in self._subscripions:
            self._tasks.append(asyncio.create_task(self._consume(subscription_id, callback=callback, *args, **kwargs)))
            self._tasks.append(asyncio.create_task(self._subscribe(payload, subscription_id, auth=True)))
        else:
            self._log.info(f"Already subscribed to {subscription_id}")
