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
from tradebot.exceptions import OrderError
from tradebot.entity import EventSystem, Order
from tradebot.base import ExchangeManager, OrderManager, AccountManager, WebsocketManager





class BinanceExchangeManager(ExchangeManager):
    pass

class BinanceOrderManager(OrderManager):
    def __init__(self, exchange: BinanceExchangeManager):
        super().__init__(exchange)
        self.exchange_id = exchange.config['exchange_id']
    
    async def handle_request_timeout(self, method: str, params: Dict[str, Any]):
        symbol = params['symbol']
        current_time = int(time.time() * 1000)
        orders = await self.fetch_orders(symbol, since = current_time - 1000 * 5)
        
        if not in_orders(orders, method, params):
            match method:
                case "place_limit_order":
                    return await self.retry_place_limit_order(params)
                case "place_market_order":
                    return await self.retry_place_market_order(params)
                case "cancel_order":
                    return await self.retry_cancel_order(params)
            
    async def place_limit_order(
        self, 
        symbol: str, 
        side: Literal['buy', 'sell'], 
        amount: Decimal, 
        price: float, 
        **params
    ) -> Order:
        res = await super().place_limit_order(symbol, side, amount, price, **params)
        if isinstance(res, OrderError):
            self._log.error(str(res))
            return Order(
                raw={},
                success=False,
                exchange=self.exchange_id,
                id=None,
                client_order_id=None,
                timestamp=int(time.time() * 1000),
                symbol=symbol,
                type='limit',
                side=side,
                status='failed',
                price=price,
                amount=amount,
            )
        return parse_ccxt_order(res, self.exchange_id)

    async def place_market_order(
        self, 
        symbol: str, 
        side: Literal['buy', 'sell'], 
        amount: Decimal, 
        **params
    ) -> Order:
        res = await super().place_market_order(symbol, side, amount, **params)
        if isinstance(res, OrderError):
            self._log.error(str(res))
            return Order(
                raw={},
                success=False,
                exchange=self.exchange_id,
                id=None,
                client_order_id=None,
                timestamp=int(time.time() * 1000),
                symbol=symbol,
                type='market',
                side=side,
                status='failed',
                amount=amount,
            )
        return parse_ccxt_order(res, self.exchange_id)
    
    async def cancel_order(self, id: str, symbol: str, **params) -> Order:
        res = await super().cancel_order(id, symbol, **params)
        if isinstance(res, OrderError):
            self._log.error(str(res))
            return Order(
                raw={},
                success=False,
                exchange=self.exchange_id,
                id=id,
                client_order_id=None,
                timestamp=int(time.time() * 1000),
                symbol=symbol,
                type=None,
                side=None,
                status='failed',
                amount=None,
            )
        return parse_ccxt_order(res, self.exchange_id)
        
    async def fetch_orders(self, symbol: str, since: int = None, limit: int = None) -> List[Order]:
        res = await self._exchange.api.fetch_orders(
            symbol = symbol,
            since=since,
            limit=limit
        )    
        return [parse_ccxt_order(order, self.exchange_id) for order in res]
    
    async def _create_order(self, symbol, type, side, amount, price, **params):
        res = await self._exchange.api.create_order(
            symbol=symbol,
            type=type,
            side=side,
            amount=amount,
            price=price,
            params=params
        )
        return parse_ccxt_order(res, self._exchange.config['exchange_id'])
       
    
    
    async def retry_place_limit_order(self, params: Dict[str, Any], max_retry: int = 3, interval: int = 3):
        params['handle_timeout'] = False
        for i in range(max_retry):
            res = await super().place_limit_order(**params)
            
            if not isinstance(res, OrderError):
                return res
            
            if i == max_retry - 1:
                return Order(
                    raw={},
                    success=False,
                    exchange=self.exchange_id,
                    id=params.get('id', None),
                    client_order_id='',
                    timestamp=int(time.time() * 1000),
                    symbol=params.get('symbol', None),
                    type='limit',
                    side=params['side'],
                    price=params.get('price', None),
                    amount=params.get('amount', None),
                    status='failed'
                )
            
            self._log.warn(f"Order placement failed, attempting retry {i+1} of {max_retry}: {str(res)}")
            await asyncio.sleep(interval)
    
    async def retry_place_market_order(self, params: Dict[str, Any], max_retry: int = 3, interval: int = 3):
        params['handle_timeout'] = False
        for i in range(max_retry):
            res = await super().place_market_order(**params)
            
            if not isinstance(res, OrderError):
                return res
            
            if i == max_retry - 1:
                return Order(
                    raw={},
                    success=False,
                    exchange=self.exchange_id,
                    id=params.get('id', None),
                    client_order_id='',
                    timestamp=int(time.time() * 1000),
                    symbol=params.get('symbol', None),
                    type='market',
                    side=params.get('side', None),
                    amount=params.get('amount', None),
                    status='failed'
                )
            
            self._log.warn(f"Order placement failed, attempting retry {i+1} of {max_retry}: {str(res)}")
            await asyncio.sleep(interval)
    

    async def retry_cancel_order(self, params: Dict[str, Any], max_retry: int = 3, interval: int = 3):
        params['handle_timeout'] = False
        for i in range(max_retry):
            res = await super().cancel_order(**params)
            
            if not isinstance(res, OrderError):
                return res
            
            if i == max_retry - 1:
                return Order(
                    raw={},
                    success=False,
                    exchange=self._exchange.config['exchange_id'],
                    id=params.get('id', None),
                    client_order_id='',
                    timestamp=int(time.time() * 1000),
                    symbol=params.get('symbol', None),
                    type=params.get('type', None),
                    side=params.get('side', None),
                    status='failed',
                    amount=params.get('amount', None),
                )
            
            self._log.warn(f"Order cancellation failed, attempting retry {i+1} of {max_retry}: {str(res)}")
            await asyncio.sleep(interval)
        
        
        
        
    
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



def in_orders(orders: List[Order], method: str, params: Dict[str, Any]) -> bool:
    for order in orders:
        match method:
            case "place_limit_order":
                if (
                    order.symbol == params['symbol']
                    and order.side == params['side']
                    and order.amount == params['amount']
                    and order.price == params['price']
                    and order.type == 'limit'
                ):
                    return True
            case "place_market_order":
                if (
                    order.symbol == params['symbol']
                    and order.side == params['side']
                    and order.amount == params['amount']
                    and order.type == 'market'
                ):
                    return True
            case "cancel_order":
                if (
                    order.symbol == params['symbol']
                    and order.id == params['id']
                    and order.status == 'canceled'
                ):
                    return True



def parse_ccxt_order(res: Dict[str, Any], exchange: str) -> Order:
    raw = res.get('info', {})
    id = res.get('id', None)
    client_order_id = res.get('clientOrderId', None)
    timestamp = res.get('timestamp', None)
    symbol = res.get('symbol', None)
    type = res.get('type', None) # market or limit
    side = res.get('side', None) # buy or sell
    price = res.get('price', None) # maybe empty for market order
    average = res.get('average', None) # float everage filling price
    amount = res.get('amount', None)
    filled = res.get('filled', None)
    remaining = res.get('remaining', None)
    status = raw.get('status', None).lower()
    cost = res.get('cost', None)
    reduce_only = raw.get('reduceOnly', None)
    position_side = raw.get('positionSide', '').lower() or None # long or short
    time_in_force = res.get('timeInForce', None)
    
    return Order(
        raw=raw,
        success=True,
        exchange=exchange,
        id=id,
        client_order_id=client_order_id,
        timestamp=timestamp,
        symbol=symbol,
        type=type,
        side=side,
        price=price,
        average=average,
        amount=amount,
        filled=filled,
        remaining=remaining,
        status=status,
        cost=cost,
        reduce_only=reduce_only,
        position_side=position_side,
        time_in_force=time_in_force
    )



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
                "e": "ORDER_TRADE_UPDATE", // Event type
                "T": 1727352962757,  // Transaction time
                "E": 1727352962762, // Event time
                "fs": "UM", // Event business unit. 'UM' for USDS-M futures and 'CM' for COIN-M futures
                "o": {
                    "s": "NOTUSDT", // Symbol
                    "c": "c-11WLU7VP1727352880uzcu2rj4ss0i", // Client order ID
                    "S": "SELL", // Side
                    "o": "LIMIT", // Order type
                    "f": "GTC", // Time in force
                    "q": "5488", // Original quantity
                    "p": "0.0084830", // Original price
                    "ap": "0", // Average price
                    "sp": "0", // Ignore
                    "x": "NEW", // Execution type
                    "X": "NEW", // Order status
                    "i": 4968510801, // Order ID
                    "l": "0", // Order last filled quantity
                    "z": "0", // Order filled accumulated quantity
                    "L": "0", // Last filled price
                    "n": "0", // Commission, will not be returned if no commission
                    "N": "USDT", // Commission asset, will not be returned if no commission
                    "T": 1727352962757, // Order trade time
                    "t": 0, // Trade ID
                    "b": "0", // Bids Notional
                    "a": "46.6067521", // Ask Notional
                    "m": false, // Is this trade the maker side?
                    "R": false, // Is this reduce only
                    "ps": "BOTH", // Position side
                    "rp": "0", // Realized profit of the trade
                    "V": "EXPIRE_NONE", // STP mode
                    "pm": "PM_NONE", 
                    "gtd": 0
                }
            }
            """
            if (event_data := event_data.get('o', None)):
            
                if (market := market_id.get(event_data['s'], None)) is None:
                    id = f"{event_data['s']}_swap"
                    market = market_id[id]    
                
                if (type := event_data['o'].lower()) == "market":
                    cost = float(event_data.get('l', '0')) * float(event_data.get('ap', '0'))
                elif type == "limit":
                    price = float(event_data.get('ap', '0')) or float(event_data.get('p', '0')) # if average price is 0 or empty, use price
                    cost = float(event_data.get('l', '0')) * price
                
                return Order(
                    raw = event_data,
                    success = True,
                    exchange = "binance",
                    id = event_data.get('i', None),
                    client_order_id=event_data.get('c', None),
                    timestamp=event_data.get('T', None),
                    symbol=market['symbol'],
                    type = type,
                    side = event_data.get('S', '').lower(),
                    status=event_data.get('X', '').lower(),
                    price = event_data.get('p', None),
                    average=event_data.get('ap', None),
                    last_filled_price=event_data.get('L', None),
                    amount=event_data.get('q', None),
                    filled=event_data.get('z', None),
                    last_filled=event_data.get('l', None),
                    remaining=Decimal(event_data['q']) - Decimal(event_data['z']),
                    fee=event_data.get('n', None),
                    fee_currency=event_data.get('N', None),
                    cost=cost,
                    last_trade_timestamp=event_data.get('T', None),
                    reduce_only=event_data.get('R', None),
                    position_side=event_data.get('ps','').lower(),
                    time_in_force=event_data.get('f', None)
                )
        
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
                "e": "executionReport", // Event type
                "E": 1727353057267, // Event time
                "s": "ORDIUSDT", // Symbol
                "c": "c-11WLU7VP2rj4ss0i", // Client order ID 
                "S": "BUY", // Side
                "o": "MARKET", // Order type
                "f": "GTC", // Time in force
                "q": "0.50000000", // Order quantity
                "p": "0.00000000", // Order price
                "P": "0.00000000", // Stop price
                "g": -1, // Order list id
                "x": "TRADE", // Execution type
                "X": "PARTIALLY_FILLED", // Order status
                "i": 2233880350, // Order ID
                "l": "0.17000000", // last executed quantity
                "z": "0.17000000", // Cumulative filled quantity
                "L": "36.88000000", // Last executed price
                "n": "0.00000216", // Commission amount
                "N": "BNB", // Commission asset
                "T": 1727353057266, // Transaction time
                "t": 105069149, // Trade ID
                "w": false, // Is the order on the book?
                "m": false, // Is this trade the maker side?
                "O": 1727353057266, // Order creation time
                "Z": "6.26960000", // Cumulative quote asset transacted quantity
                "Y": "6.26960000", // Last quote asset transacted quantity (i.e. lastPrice * lastQty)
                "V": "EXPIRE_MAKER", // Self trade prevention Mode
                "I": 1495839281094 // Ignore
            }
            
            # Example of an execution report event for a partially filled market buy order
            {
                "e": "executionReport", // Event type
                "E": 1727353057267, // Event time
                "s": "ORDIUSDT", // Symbol
                "c": "c-11WLU7VP2rj4ss0i", // Client order ID 
                "S": "BUY", // Side
                "o": "MARKET", // Order type
                "f": "GTC", // Time in force
                "q": "0.50000000", // Order quantity
                "p": "0.00000000", // Order price
                "P": "0.00000000", // Stop price
                "g": -1, // Order list id
                "x": "TRADE", // Execution type
                "X": "PARTIALLY_FILLED", // Order status
                "i": 2233880350, // Order ID
                "l": "0.17000000", // last executed quantity
                "z": "0.34000000", // Cumulative filled quantity
                "L": "36.88000000", // Last executed price
                "n": "0.00000216", // Commission amount
                "N": "BNB", // Commission asset
                "T": 1727353057266, // Transaction time
                "t": 105069150, // Trade ID
                "w": false, // Is the order on the book?
                "m": false, // Is this trade the maker side?
                "O": 1727353057266, // Order creation time
                "Z": "12.53920000", // Cumulative quote asset transacted quantity
                "Y": "6.26960000", // Last quote asset transacted quantity (i.e. lastPrice * lastQty)
                "V": "EXPIRE_MAKER", // Self trade prevention Mode
                "I": 1495839281094 // Ignore
            }
            
            """
            id = f"{event_data['s']}_spot"
            market = market_id[id]
            
            
            return Order(
                raw = event_data,
                success = True,
                exchange = "binance",
                id = event_data.get('i', None),
                client_order_id=event_data.get('c', None),
                timestamp=event_data.get('T', None),
                symbol=market['symbol'],
                type = event_data.get('o', '').lower(),
                side = event_data.get('S', '').lower(),
                status=event_data.get('X', '').lower(),
                price = event_data.get('p', None),
                average=event_data.get('ap', None),
                last_filled_price=event_data.get('L', None),
                amount=event_data.get('q', None),
                filled=event_data.get('z', None),
                last_filled=event_data.get('l', None),
                remaining=Decimal(event_data.get('q', '0')) - Decimal(event_data.get('z', '0')),
                fee=event_data.get('n', None),
                fee_currency=event_data.get('N', None),
                cost=event_data.get('Y', None),
                last_trade_timestamp=event_data.get('T', None),
                time_in_force=event_data.get('f', None)
            )
            
            
            
            
        
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
