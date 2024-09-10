import json
import asyncio


from typing import Any, Dict
from typing import Literal


import orjson
import aiohttp
import websockets


from asynciolimiter import Limiter
from websockets.asyncio import client


from tradebot.constants import MARKET_URLS
from tradebot.entity import EventSystem
from tradebot.base import ExchangeManager, OrderManager, AccountManager, WebsocketManager





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
    
    async def _user_data_stream(self, listen_key:str, typ: Literal['spot', 'linear', 'inverse', 'portfolio']):
        stream_url = MARKET_URLS["binance"][typ]['stream_url']
        ws_url = f"{stream_url}{listen_key}"
        
        queue_id = f"{typ}_user_data"
        self.queues[queue_id] = asyncio.Queue()
        self.tasks.append(asyncio.create_task(self.consume(queue_id, callback=self._user_data_callback)))
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
                 close_timeout: int = 1, max_queue: int = 12):
        super().__init__(config, ping_interval, ping_timeout, close_timeout, max_queue)
        self.rate_limiter = Limiter(3/1)
        
    
    async def _subscribe(self, symbol: str, typ: Literal["spot", "linear"], channel: Literal["books", "books5", "bbo-tbt", "trades"], queue_id: str):
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
                    uri="wss://ws.okx.com:8443/ws/v5/public",
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
