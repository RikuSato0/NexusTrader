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
from typing import Literal, Callable, Optional


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




def parse_websocket_stream(event_data: Dict[str, Any], market_id: Dict[str, Any], market_type: Optional[Literal["spot", "swap"]] = None):
    event = event_data.get('e', None)
    match event:
        case "kline":
            """
            {
                'e': 'kline', 
                'E': 1727525244267, 
                's': 'BTCUSDT', 
                'k': {
                    't': 1727525220000, 
                    'T': 1727525279999, 
                    's': 'BTCUSDT', 
                    'i': '1m', 
                    'f': 5422081499, 
                    'L': 5422081624, 
                    'o': '65689.80', 
                    'c': '65689.70', 
                    'h': '65689.80', 
                    'l': '65689.70', 
                    'v': '9.027', 
                    'n': 126, 
                    'x': False, 
                    'q': '592981.58290', 
                    'V': '6.610', 
                    'Q': '434209.57800', 
                    'B': '0'
                }
            }
            """
            id = f"{event_data['s']}_{market_type}" if market_type else event_data['s']
            market = market_id[id]
            event_data['s'] = market['symbol']
            return event_data


def parse_user_data_stream(event_data: Dict[str, Any], market_id: Dict[str, Any]):
    event = event_data.get('e', None)
    match event:
        case "ORDER_TRADE_UPDATE":
            """
            {
                "e": "ORDER_TRADE_UPDATE", 
                "T": 1727352962757, 
                "E": 1727352962762, 
                "fs": "UM", 
                "o": {
                    "s": "NOTUSDT", 
                    "c": "c-11WLU7VP1727352880uzcu2rj4ss0i", 
                    "S": "SELL", 
                    "o": "LIMIT", 
                    "f": "GTC", 
                    "q": "5488", 
                    "p": "0.0084830", 
                    "ap": "0", 
                    "sp": "0", 
                    "x": "NEW", 
                    "X": "NEW", 
                    "i": 4968510801, 
                    "l": "0", 
                    "z": "0", 
                    "L": "0", 
                    "n": "0", 
                    "N": "USDT", 
                    "T": 1727352962757, 
                    "t": 0, 
                    "b": "0", 
                    "a": "46.6067521", 
                    "m": false, 
                    "R": false, 
                    "ps": "BOTH", 
                    "rp": "0", 
                    "V": "EXPIRE_NONE", 
                    "pm": "PM_NONE", 
                    "gtd": 0
                }
            }
            """
            if (market := market_id.get(event_data['o']['s'], None)) is None:
                id = f"{event_data['o']['s']}_swap"
                market = market_id[id]
            event_data['o']['s'] = market['symbol']
            return event_data
        
        case "ACCOUNT_UPDATE":
            """
            {
                "e": "ACCOUNT_UPDATE", 
                "T": 1727352914268, 
                "E": 1727352914274, 
                "fs": "UM", 
                "a": {
                    "B": [
                        {"a": "USDT", "wb": "0.07147421", "cw": "0.07147421", "bc": "0"}, 
                        {"a": "BNB", "wb": "0.01993701", "cw": "0.01993701", "bc": "0"}
                    ], 
                    "P": [
                        {
                            "s": "BOMEUSDT", 
                            "pa": "-2760", 
                            "ep": "0.00724500", 
                            "cr": "0", 
                            "up": "-0.00077280", 
                            "ps": "BOTH", 
                            "bep": 0.0072436959
                        }
                    ], 
                "m": "ORDER"
                }
            }
            """
            positions = []
            for position in event_data['a']['P']:
                if (market := market_id.get(position['s'], None)) is None:
                    id = f"{position['s']}_swap"
                    market = market_id[id]
                position['s'] = market['symbol']
                positions.append(position)
            event_data['a']['P'] = positions
            return event_data
        
        case "balanceUpdate":
            """
            {
                "e": "balanceUpdate", 
                "E": 1727320813969, 
                "a": "BNB", 
                "d": "-0.01000000", 
                "U": 1495297874797, 
                "T": 1727320813969
            }
            """
            return event_data
        
        case "executionReport":
            """
            {
                "e": "executionReport", 
                "E": 1727353057267, 
                "s": "ORDIUSDT", 
                "c": "c-11WLU7VP2rj4ss0i", 
                "S": "BUY", 
                "o": "MARKET", 
                "f": "GTC", 
                "q": "0.50000000", 
                "p": "0.00000000", 
                "P": "0.00000000", 
                "g": -1, 
                "x": "TRADE", 
                "X": "PARTIALLY_FILLED", 
                "i": 2233880350, 
                "l": "0.17000000", 
                "z": "0.17000000", 
                "L": "36.88000000", 
                "n": "0.00000216", 
                "N": "BNB", 
                "T": 1727353057266, 
                "t": 105069149, 
                "w": false, 
                "m": false, 
                "O": 1727353057266, 
                "Z": "6.26960000", 
                "Y": "6.26960000", 
                "V": "EXPIRE_MAKER", 
                "I": 1495839281094
            }
            """
            id = f"{event_data['s']}_spot"
            market = market_id[id]
            event_data['s'] = market['symbol']
            return event_data
        
        case "outboundAccountPosition":
            """
            {
                "e": "outboundAccountPosition", 
                "E": 1727353873873, 
                "u": 1727353873873, 
                "U": 1495859325408, 
                "B": [
                    {
                        "a": "BNB", 
                        "f": 
                        "0.09971173", 
                        "l": 
                        "0.00000000"
                    }, 
                    {
                        "a": "USDT", 
                        "f": "6426.31521496", 
                        "l": "0.00000000"
                    }, 
                    {"a": 
                    "AVAX", 
                    "f": "3.00000000", 
                    "l": "0.00000000"
                    }
                ]
            }
            """
            return event_data
