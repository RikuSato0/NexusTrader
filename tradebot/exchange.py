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
from typing import Literal, Callable



import orjson
import aiohttp
import websockets
import ccxt.pro as ccxtpro

from asynciolimiter import Limiter
from websockets.asyncio import client


from tradebot.constants import IntervalType, UrlType
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
    def __init__(self, exchange: BinanceExchangeManager):
        super().__init__(exchange)
    

class BinanceAccountManager(AccountManager):
    pass

class BinanceWebsocketManager(WebsocketManager):
    def __init__(self, url: UrlType, api_key: str = None, secret: str = None):
        super().__init__(
            base_url=url.STREAM_URL,
            ping_interval=5,
            ping_timeout=5,
            close_timeout=1,
            max_queue=12,
        )
        self._url = url
        self._api_key = api_key
        self._secret = secret
        self._session: aiohttp.ClientSession = None
    
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
    
    async def subscribe_kline(self, symbol: str, interval: IntervalType, callback: Callable[..., Any] = None, *args, **kwargs):
        subscription_id = f"kline.{symbol}.{interval}"
        id = int(time.time() * 1000)
        payload = {
            "method": "SUBSCRIBE",
            "params": [f"{symbol.lower()}@kline_{interval}"],
            "id": id
        }
        if subscription_id not in self._subscripions:
            self._tasks.append(asyncio.create_task(self._consume(subscription_id, callback=callback, *args, **kwargs)))
            self._tasks.append(asyncio.create_task(self._subscribe(payload, subscription_id)))
        else:
            self._log.info(f"Already subscribed to {subscription_id}")
    
    async def subscribe_klines(self, symbols: List[str], interval: IntervalType, callback: Callable[..., Any] = None, *args, **kwargs):
        for symbol in symbols:
            await self.subscribe_kline(symbol, interval, callback=callback, *args, **kwargs)

    async def subscribe_user_data(self, callback: Callable[..., Any] = None, *args, **kwargs):
        type = self._url.__name__.lower()
        subscription_id = f"user_data.{type}"
        
        listen_key = await self._get_listen_key()
        payload = {
            "method": "SUBSCRIBE",
            "params": [listen_key],
            "id": int(time.time() * 1000)
        }
        if subscription_id not in self._subscripions:
            self._tasks.append(asyncio.create_task(self._keep_alive_listen_key(listen_key)))
            self._tasks.append(asyncio.create_task(self._consume(subscription_id, callback=callback, *args, **kwargs)))
            self._tasks.append(asyncio.create_task(self._subscribe(payload, subscription_id)))
        else:
            self._log.info(f"Already subscribed to {subscription_id}")
    
    async def _get_listen_key(self):
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={"X-MBX-APIKEY": self._api_key}
            )
        try:
            async with self._session.post(self._url.BASE_URL) as response:
                data = await response.json()
                return data["listenKey"]
        except Exception as e:
            self._log.error(f"Failed to get listen key: {e}")
            return None
    
    async def _keep_alive_listen_key(self, listen_key: str):
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={"X-MBX-APIKEY": self._api_key}
            )
        base_url = self._url.BASE_URL
        type = self._url.__name__.lower()
        while True:
            try:
                self._log.info(f'Keep alive {type} listen key...')
                async with self._session.put(f'{base_url}?listenKey={listen_key}') as response:
                    self._log.info(f"Keep alive listen key status: {response.status}")
                    if response.status != 200:
                        listen_key = await self._get_listen_key()
                    else:
                        data = await response.json()
                        self._log.info(f"Keep alive {type} listen key: {data.get('listenKey', listen_key)}")
                    await asyncio.sleep(60 * 20)
            except asyncio.CancelledError:
                self._log.info(f"Cancelling keep alive task for {type} listen key")
                break        
            except Exception as e:
                self._log.error(f"Error keeping alive {type} listen key: {e}")
    
    async def close(self):
        if self._session is not None:
            await self._session.close()
        await super().close()
        




class OkxExchangeManager(ExchangeManager):
    pass

class OkxOrderManager(OrderManager):
    def __init__(self, exchange: OkxExchangeManager):
        super().__init__(exchange)

class OkxAccountManager(AccountManager):
    pass

class OkxWebsocketManager(WebsocketManager):
    def __init__(self, url: UrlType, api_key: str = None, secret: str = None, passphrase: str = None):
        super().__init__(
            base_url=url,
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
        subscription_id = f"position.{inst_type}"
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
    
    async def subscribe_order(self, inst_type: Literal["SPOT", "MARGIN", "SWAP", "FUTURES", "OPTION", "ANY"] = "ANY", callback: Callable[..., Any] = None, *args, **kwargs):
        subscription_id = f"order.{inst_type}"
        payload = {
            "op": "subscribe",
            "args": [{
                "channel": "orders",
                "instType": inst_type
            }]
        }
        if subscription_id not in self._subscripions:
            self._tasks.append(asyncio.create_task(self._consume(subscription_id, callback=callback, *args, **kwargs)))
            self._tasks.append(asyncio.create_task(self._subscribe(payload, subscription_id, auth=True)))
        else:
            self._log.info(f"Already subscribed to {subscription_id}")
    
    async def subscribe_fills(self, callback: Callable[..., Any] = None, *args, **kwargs):
        subscription_id = "fills"
        payload = {
            "op": "subscribe",
            "args": [{
                "channel": "fills"
            }]
        }
        if subscription_id not in self._subscripions:
            self._tasks.append(asyncio.create_task(self._consume(subscription_id, callback=callback, *args, **kwargs)))
            self._tasks.append(asyncio.create_task(self._subscribe(payload, subscription_id, auth=True)))
        else:
            self._log.info(f"Already subscribed to {subscription_id}")
