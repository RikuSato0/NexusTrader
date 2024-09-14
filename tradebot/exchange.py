import base64
import hmac
import json
import time

import requests
import asyncio


from typing import Any, Dict, List
from typing import Literal, Callable


import orjson
import aiohttp
import websockets


from asynciolimiter import Limiter
from websockets.asyncio import client


from tradebot.constants import MARKET_URLS
from tradebot.entity import EventSystem
from tradebot.base import ExchangeManager, OrderManager, AccountManager, WebsocketManager




class BybitExchangeManager(ExchangeManager):
    pass

class BybitOrderManager(OrderManager):
    pass

class BybitAccountManager(AccountManager):
    pass

class BybitWebsocketManager(WebsocketManager):
    pass




class BinanceExchangeManager(ExchangeManager):
    pass

class BinanceOrderManager(OrderManager):
    pass

class BinanceAccountManager(AccountManager):
    pass

class BinanceWebsocketManager(WebsocketManager):
    def __init__(self, config: Dict[str, Any] = None, 
                 ping_interval: int = 5, 
                 ping_timeout: int = 5, 
                 close_timeout: int = 1, 
                 max_queue: int = 12):
        
        super().__init__(config, ping_interval, ping_timeout, close_timeout, max_queue)
        
        self.rate_limiter = Limiter(10/1) # 10 requests per second
        self.session: aiohttp.ClientSession = None

    async def _subscribe(self, symbol: str, typ: Literal["spot", "linear"], channel: Literal['trade', 'bookTicker'], queue_id: str):
        s = symbol.replace('/USDT', 'USDT')
        ws_url = MARKET_URLS["binance"][typ]["stream_url"]
        
        while True:
            try:
                await self.rate_limiter.wait()
                uri = f"{ws_url}{s.lower()}@{channel}"
                async with client.connect(
                    uri=uri,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout,
                    close_timeout=self.close_timeout,
                    max_queue=self.max_queue
                ) as ws:
                    self.logger.info(f"Connected to {symbol} for {queue_id}")
                    async for msg in ws:
                        msg = orjson.loads(msg)
                        await self.queues[queue_id].put(msg)
            except websockets.exceptions.ConnectionClosed as e:
                self.logger.info(f"Connection closed for {symbol} in {queue_id}. Reconnecting...")
            except asyncio.CancelledError:
                self.logger.info(f"Cancelling watch task for {symbol} in {queue_id}")
                break
            except Exception as e:
                self.logger.error(f"Error in watch for {symbol} in {queue_id}: {e}")
                await asyncio.sleep(3)
    
    async def _get_listen_key(self, base_url: str):
        if self.session is None:
            self.session = aiohttp.ClientSession(headers={'X-MBX-APIKEY': self.api_key})
        try:
            async with self.session.post(base_url) as res:
                data = await res.json()
                return data['listenKey']
        except Exception as e:
            self.logger.error(f"Error getting listen key: {e}")
            return None
    
    async def _keep_alive_listen_key(self, listen_key: str, typ: Literal['spot', 'linear', 'inverse', 'portfolio']):
        if self.session is None:
            self.session = aiohttp.ClientSession(headers={'X-MBX-APIKEY': self.api_key})
        base_url = MARKET_URLS["binance"][typ]['base_url']
        while True:
            try:
                self.logger.info(f'Keep alive {typ} listen key...')
                async with self.session.put(f'{base_url}?listenKey={listen_key}') as res:
                    self.logger.info(f"Keep alive listen key status: {res.status}")
                    if res.status != 200:
                        listen_key = await self._get_listen_key(base_url)
                    else:
                        data = await res.json()
                        self.logger.info(f"Keep alive {typ} listen key: {data.get('listenKey', listen_key)}")
                    await asyncio.sleep(60 * 20)
            except asyncio.CancelledError:
                self.logger.info(f"Cancelling keep alive task for {typ} listen key")
                break        
            except Exception as e:
                self.logger.error(f"Error keeping alive {typ} listen key: {e}")
    
    async def user_data_stream(self, listen_key:str, typ: Literal['spot', 'linear', 'inverse', 'portfolio'], callback: Callable[..., Any] = None, *args, **kwargs):
        stream_url = MARKET_URLS["binance"][typ]['stream_url']
        ws_url = f"{stream_url}{listen_key}"
        
        queue_id = f"{typ}_user_data"
        self.queues[queue_id] = asyncio.Queue()
        self.tasks.append(asyncio.create_task(self.consume(queue_id, callback=callback, *args, **kwargs)))
        while True:
            try:
                async with client.connect(ws_url, ping_interval=5, ping_timeout=5, close_timeout=1, max_queue=24) as websocket:
                    self.logger.info(f"Connected to {typ} user data stream...")
                    async for message in websocket:
                        res = orjson.loads(message)
                        self.logger.info(f"user data stream: {res}")
                        await self.queues[queue_id].put(res)
            except websockets.ConnectionClosed:
                self.logger.error(f"Connection closed, reconnecting...")
            except asyncio.CancelledError:
                self.logger.info(f"Cancelling {typ} user data stream...")
                break
            except Exception as e:
                self.logger.error(f"Error in watch {typ} user data stream: {e}")
                await asyncio.sleep(3)
    
    async def _user_data_callback(msg):
        if msg['e'] == 'executionReport':
            await EventSystem.emit('binance_order_update', msg, 'spot')
        elif msg['e'] == 'ORDER_TRADE_UPDATE':
            await EventSystem.emit('binance_order_update', msg, 'linear')
        elif msg['e'] == 'ACCOUNT_UPDATE':
            await EventSystem.emit('binance_account_update', msg, 'linear')
        elif msg['e'] == 'outboundAccountPosition':
            await EventSystem.emit('binance_account_update', msg, 'spot')
    

    async def close(self):
        await super().close()
        await self.session.close()



class OkxExchangeManager(ExchangeManager):
    pass

class OkxOrderManager(OrderManager):
    pass

class OkxAccountManager(AccountManager):
    pass

class OkxWebsocketManager(WebsocketManager):
    def __init__(self, 
                 config: Dict[str, Any] = None, ping_interval: int = 5, 
                 ping_timeout: int = 5, 
                 close_timeout: int = 1, max_queue: int = 12, demo_trade: bool = False):
        super().__init__(config, ping_interval, ping_timeout, close_timeout, max_queue)
        self.rate_limiter = Limiter(3/1)
        self.demo_trade = demo_trade
        
    def init_login_params(self, api_key: str, passphrase: str, secret: str):
        timestamp = self._get_server_time()
        message = str(timestamp) + 'GET' + '/users/self/verify'
        mac = hmac.new(bytes(secret, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
        d = mac.digest()
        sign = base64.b64encode(d)
        arg = {"apiKey": api_key, "passphrase": passphrase, "timestamp": timestamp, "sign": sign.decode("utf-8")}
        payload = {"op": "login", "args": [arg]}
        return json.dumps(payload)

    def _get_server_time(self):
        url = "https://www.okx.com/api/v5/public/time"
        response = requests.get(url)
        if response.status_code == 200:
            timestamp = int(int(response.json()['data'][0]['ts']) / 1000)
            return str(timestamp)
        else:
            return ""
    
    async def _subscribe(self, symbol: str, typ: Literal["spot", "linear"], channel: Literal["books", "books5", "bbo-tbt", "trades"], queue_id: str):
        """
        Subscribes to a specific symbol and channel on the exchange WebSocket.
        Api documentation: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-ws-order-book-channel
        
        Args:
            symbol (str): The trading symbol to subscribe to.
            typ (Literal["spot", "linear"]): The type of trading (spot or linear).
            channel (Literal["books", "books5", "bbo-tbt", "trades"]): The channel to subscribe to.
            queue_id (str): The ID of the queue to store the received messages.
            
        Returns:
            None
        """
        if typ == "spot":
            s = symbol.replace('/USDT', '-USDT')
        else:
            s = symbol.replace('/USDT', '-USDT-SWAP')
        params = [{
            "channel": channel,
            "instId": s
        }]
        
        while True:
            try:
                await self.rate_limiter.wait()
                async with client.connect(
                    uri=MARKET_URLS["okx"]["demo"]["public"] if self.demo_trade else MARKET_URLS["okx"]["live"]["public"],
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout,
                    close_timeout=self.close_timeout,
                    max_queue=self.max_queue
                ) as ws:
                    self.logger.info(f"Connected to {symbol} for {queue_id}")
                    payload = json.dumps({
                        "op": "subscribe",
                        "args": params
                    })
                    await ws.send(payload)
                    
                    async for msg in ws:
                        msg = orjson.loads(msg)
                        await self.queues[queue_id].put(msg)
            except websockets.exceptions.ConnectionClosed as e:
                self.logger.info(f"Connection closed for {queue_id}. Reconnecting...")
            except asyncio.CancelledError:
                self.logger.info(f"Cancelling watch task for {queue_id}")
                break
            except Exception as e:
                self.logger.error(f"Error in watch for {queue_id}: {e}")
                await asyncio.sleep(3)
    
    async def _private_subscribe(self, params: List[Dict[str, Any]], queue_id: str):
        while True:
            try:
                await self.rate_limiter.wait()
                async with client.connect(
                    uri=MARKET_URLS["okx"]["demo"]["private"] if self.demo_trade else MARKET_URLS["okx"]["live"]["private"],
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout,
                    close_timeout=self.close_timeout,
                    max_queue=self.max_queue
                ) as ws:
                    self.logger.info(f"Connected to {queue_id}")
                    
                    login_payload = self.init_login_params(self.api_key, self.password, self.secret)
                    await ws.send(login_payload)
                    await asyncio.sleep(5) # wait for login 
                    payload = json.dumps({
                        "op": "subscribe",
                        "args": params
                    })
                    await ws.send(payload)
                    
                    async for msg in ws:
                        msg = orjson.loads(msg)
                        await self.queues[queue_id].put(msg)
            except websockets.exceptions.ConnectionClosed as e:
                self.logger.info(f"Connection closed for {queue_id}. Reconnecting...")
            except asyncio.CancelledError:
                self.logger.info(f"Cancelling watch task for {queue_id}")
                break
            except Exception as e:
                self.logger.error(f"Error in watch for {queue_id}: {e}")
                await asyncio.sleep(3)
    
    async def watch_positions(self, typ: Literal["MARGIN", "SWAP", "FUTURES", "OPTION", "ANY"] = "ANY", callback: Callable[..., Any] = None, *args, **kwargs):
        params = [{
            "channel": "positions",
            "instType": typ
        }]
        queue_id = f"{typ}_positions"
        self.queues[queue_id] = asyncio.Queue()
        self.tasks.append(asyncio.create_task(self.consume(queue_id, callback=callback, *args, **kwargs)))
        self.tasks.append(asyncio.create_task(self._private_subscribe(params, queue_id)))
    
    async def watch_account(self, callback: Callable[..., Any] = None, *args, **kwargs):
        params = [{
            "channel": "account"
        }]
        queue_id = "account"
        self.queues[queue_id] = asyncio.Queue()
        self.tasks.append(asyncio.create_task(self.consume(queue_id, callback=callback, *args, **kwargs)))
        self.tasks.append(asyncio.create_task(self._private_subscribe(params, queue_id)))

    async def watch_orders(self, typ: Literal["SPOT", "MARGIN", "SWAP", "FUTURES", "OPTION", "ANY"] = "ANY", callback: Callable[..., Any] = None, *args, **kwargs):
        params = [{
            "channel": "orders",
            "instType": typ
        }]
        queue_id = f"{typ}_orders"
        self.queues[queue_id] = asyncio.Queue()
        self.tasks.append(asyncio.create_task(self.consume(queue_id, callback=callback, *args, **kwargs)))
        self.tasks.append(asyncio.create_task(self._private_subscribe(params, queue_id)))
    