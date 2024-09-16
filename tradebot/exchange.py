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
from tradebot.base import ExchangeManager, OrderManager, AccountManager



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

class BinanceWebsocketManager:
    def __init__(self, base_url: str):
        self._base_url = base_url
        self._ping_interval = 5
        self._ping_timeout = 5
        self._close_timeout = 1
        self._max_queue = 12
        
        self._tasks: List[asyncio.Task] = []
        self._subscripions = defaultdict(asyncio.Queue)
        self._log = log_register.get_logger(name=type(self).__name__, level="INFO", flush=True)
    
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
    
    async def _consume(self, subscription_id: str, callback: Callable[..., Any] = None, *args, **kwargs):
        while True:
            msg = await self._subscripions[subscription_id].get()
            if asyncio.iscoroutinefunction(callback):
                await callback(msg, *args, **kwargs)
            else:
                callback(msg, *args, **kwargs)
            self._subscripions[subscription_id].task_done()
    
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
    
    async def close(self):
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._log.info("All WebSocket connections closed.")
    
        
    
    
            
                
    






















class OkxExchangeManager(ExchangeManager):
    pass

class OkxOrderManager(OrderManager):
    pass

class OkxAccountManager(AccountManager):
    pass









class OkxWebsocketManager:
    def __init__(self, base_url: str, api_key: str = None, secret: str = None, passphrase: str = None):
        self._base_url = base_url
        self._ping_interval = 5
        self._ping_timeout = 5
        self._close_timeout = 1
        self._max_queue = 12
        
        self._api_key = api_key
        self._secret = secret
        self._passphrase = passphrase
        
        self._tasks: List[asyncio.Task] = []
        self._subscripions = defaultdict(asyncio.Queue)
        self._log = log_register.get_logger(name=type(self).__name__, level="INFO", flush=True)
        
        
    async def _subscribe(self, payload: Dict[str, Any], subscription_id: str, auth: bool = False):
        async for websocket in websockets.connect(
            uri = self._base_url,
            ping_interval=self._ping_interval,
            ping_timeout=self._ping_timeout,
            close_timeout=self._close_timeout,
            max_queue=self._max_queue,
        ):
            try:
                if auth:
                    payload = self._get_auth_payload()
                    await websocket.send(payload)
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

    










# class OkxWebsocketManager(WebsocketManager):
#     def __init__(self, 
#                  config: Dict[str, Any] = None, ping_interval: int = 5, 
#                  ping_timeout: int = 5, 
#                  close_timeout: int = 1, max_queue: int = 12, demo_trade: bool = False):
#         super().__init__(config, ping_interval, ping_timeout, close_timeout, max_queue)
#         self.rate_limiter = Limiter(3/1)
#         self.demo_trade = demo_trade
        
#     def init_login_params(self, api_key: str, passphrase: str, secret: str):
#         timestamp = self._get_server_time()
#         message = str(timestamp) + 'GET' + '/users/self/verify'
#         mac = hmac.new(bytes(secret, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
#         d = mac.digest()
#         sign = base64.b64encode(d)
#         arg = {"apiKey": api_key, "passphrase": passphrase, "timestamp": timestamp, "sign": sign.decode("utf-8")}
#         payload = {"op": "login", "args": [arg]}
#         return json.dumps(payload)

#     def _get_server_time(self):
#         url = "https://www.okx.com/api/v5/public/time"
#         response = requests.get(url)
#         if response.status_code == 200:
#             timestamp = int(int(response.json()['data'][0]['ts']) / 1000)
#             return str(timestamp)
#         else:
#             return ""
    
#     async def _subscribe(self, symbol: str, typ: Literal["spot", "linear"], channel: Literal["books", "books5", "bbo-tbt", "trades"], queue_id: str):
#         """
#         Subscribes to a specific symbol and channel on the exchange WebSocket.
#         Api documentation: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-ws-order-book-channel
        
#         Args:
#             symbol (str): The trading symbol to subscribe to.
#             typ (Literal["spot", "linear"]): The type of trading (spot or linear).
#             channel (Literal["books", "books5", "bbo-tbt", "trades"]): The channel to subscribe to.
#             queue_id (str): The ID of the queue to store the received messages.
            
#         Returns:
#             None
#         """
#         if typ == "spot":
#             s = symbol.replace('/USDT', '-USDT')
#         else:
#             s = symbol.replace('/USDT', '-USDT-SWAP')
#         params = [{
#             "channel": channel,
#             "instId": s
#         }]
        
#         while True:
#             try:
#                 await self.rate_limiter.wait()
#                 async with client.connect(
#                     uri=MARKET_URLS["okx"]["demo"]["public"] if self.demo_trade else MARKET_URLS["okx"]["live"]["public"],
#                     ping_interval=self.ping_interval,
#                     ping_timeout=self.ping_timeout,
#                     close_timeout=self.close_timeout,
#                     max_queue=self.max_queue
#                 ) as ws:
#                     self.logger.info(f"Connected to {symbol} for {queue_id}")
#                     payload = json.dumps({
#                         "op": "subscribe",
#                         "args": params
#                     })
#                     await ws.send(payload)
                    
#                     async for msg in ws:
#                         msg = orjson.loads(msg)
#                         await self.queues[queue_id].put(msg)
#             except websockets.exceptions.ConnectionClosed as e:
#                 self.logger.info(f"Connection closed for {queue_id}. Reconnecting...")
#             except asyncio.CancelledError:
#                 self.logger.info(f"Cancelling watch task for {queue_id}")
#                 break
#             except Exception as e:
#                 self.logger.error(f"Error in watch for {queue_id}: {e}")
#                 await asyncio.sleep(3)
    
#     async def _private_subscribe(self, params: List[Dict[str, Any]], queue_id: str):
#         while True:
#             try:
#                 await self.rate_limiter.wait()
#                 async with client.connect(
#                     uri=MARKET_URLS["okx"]["demo"]["private"] if self.demo_trade else MARKET_URLS["okx"]["live"]["private"],
#                     ping_interval=self.ping_interval,
#                     ping_timeout=self.ping_timeout,
#                     close_timeout=self.close_timeout,
#                     max_queue=self.max_queue
#                 ) as ws:
#                     self.logger.info(f"Connected to {queue_id}")
                    
#                     login_payload = self.init_login_params(self.api_key, self.password, self.secret)
#                     await ws.send(login_payload)
#                     await asyncio.sleep(5) # wait for login 
#                     payload = json.dumps({
#                         "op": "subscribe",
#                         "args": params
#                     })
#                     await ws.send(payload)
                    
#                     async for msg in ws:
#                         msg = orjson.loads(msg)
#                         await self.queues[queue_id].put(msg)
#             except websockets.exceptions.ConnectionClosed as e:
#                 self.logger.info(f"Connection closed for {queue_id}. Reconnecting...")
#             except asyncio.CancelledError:
#                 self.logger.info(f"Cancelling watch task for {queue_id}")
#                 break
#             except Exception as e:
#                 self.logger.error(f"Error in watch for {queue_id}: {e}")
#                 await asyncio.sleep(3)
    
#     async def watch_positions(self, typ: Literal["MARGIN", "SWAP", "FUTURES", "OPTION", "ANY"] = "ANY", callback: Callable[..., Any] = None, *args, **kwargs):
#         params = [{
#             "channel": "positions",
#             "instType": typ
#         }]
#         queue_id = f"{typ}_positions"
#         self.queues[queue_id] = asyncio.Queue()
#         self.tasks.append(asyncio.create_task(self.consume(queue_id, callback=callback, *args, **kwargs)))
#         self.tasks.append(asyncio.create_task(self._private_subscribe(params, queue_id)))
    
#     async def watch_account(self, callback: Callable[..., Any] = None, *args, **kwargs):
#         params = [{
#             "channel": "account"
#         }]
#         queue_id = "account"
#         self.queues[queue_id] = asyncio.Queue()
#         self.tasks.append(asyncio.create_task(self.consume(queue_id, callback=callback, *args, **kwargs)))
#         self.tasks.append(asyncio.create_task(self._private_subscribe(params, queue_id)))

#     async def watch_orders(self, typ: Literal["SPOT", "MARGIN", "SWAP", "FUTURES", "OPTION", "ANY"] = "ANY", callback: Callable[..., Any] = None, *args, **kwargs):
#         params = [{
#             "channel": "orders",
#             "instType": typ
#         }]
#         queue_id = f"{typ}_orders"
#         self.queues[queue_id] = asyncio.Queue()
#         self.tasks.append(asyncio.create_task(self.consume(queue_id, callback=callback, *args, **kwargs)))
#         self.tasks.append(asyncio.create_task(self._private_subscribe(params, queue_id)))
    