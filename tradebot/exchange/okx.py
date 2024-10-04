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
from tradebot.exceptions import OrderResponseError
from tradebot.entity import EventSystem, OrderResponse
from tradebot.base import ExchangeManager, OrderManager, AccountManager, WebsocketManager


class OkxExchangeManager(ExchangeManager):
    pass

class OkxOrderManager(OrderManager):
    def __init__(self, exchange: OkxExchangeManager):
        super().__init__(exchange)
        self.exchange_id = self._exchange.config['exchange_id']
    
    async def handle_request_timeout(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    async def place_limit_order(
        self, 
        symbol: str, 
        side: Literal['buy'] | Literal['sell'], 
        amount: Decimal, 
        price: Decimal, 
        handle_timeout: bool = True, 
        **params
    ) -> OrderResponse:
        res = await super().place_limit_order(symbol, side, amount, price, handle_timeout, **params)
        if isinstance(res, OrderResponseError):
            self._log.error(str(res))
            return OrderResponse(
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
        params.update({"price": price, "amount": amount, "side": side, "status": "new"})
        return parse_ccxt_order(res, self.exchange_id, **params)
        
    
    async def place_market_order(
        self, 
        symbol: str, 
        side: Literal['buy'] | Literal['sell'], 
        amount: Decimal, 
        handle_timeout: bool = True, 
        **params
    ) -> OrderResponse:
        res = await super().place_market_order(symbol, side, amount, handle_timeout, **params)
        if isinstance(res, OrderResponseError):
            self._log.error(str(res))
            return OrderResponse(
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
        params.update({"amount": amount, "side": side, "filled": amount, "status": "new"})
        return parse_ccxt_order(res, self.exchange_id, **params)
        
        
    
    async def cancel_order(self, id: str, symbol: str, handle_timeout: bool = True, **params) -> Dict[str, Any]:
        res = await super().cancel_order(id, symbol, handle_timeout, **params)
        if isinstance(res, OrderResponseError):
            self._log.error(str(res))
            return OrderResponse(
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
        params.update({"id": id, "symbol": symbol, "status": "canceled"})
        return parse_ccxt_order(res, self.exchange_id, **params)
    
    
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
    
    async def subscribe_positions(self, inst_type:Literal["MARGIN", "SWAP", "FUTURES", "OPTION", "ANY"] = "ANY", callback: Callable[..., Any] = None, *args, **kwargs):
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
    
    async def subscribe_orders(self, inst_type: Literal["SPOT", "MARGIN", "SWAP", "FUTURES", "OPTION", "ANY"] = "ANY", callback: Callable[..., Any] = None, *args, **kwargs):
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




def parse_ccxt_order(res: Dict[str, Any], exchange: str, **params) -> OrderResponse:
    """
    {'amount': None,
     'average': None,
     'clientOrderId': 'e847386590ce4dBC143d3105bb6368c4',
     'cost': None,
     'datetime': None,
     'fee': None,
     'fees': [],
     'filled': None,
     'id': '1862325188513431552',
     'info': {'clOrdId': 'e847386590ce4dBC143d3105bb6368c4',
             'ordId': '1862325188513431552',
             'sCode': '0',
             'sMsg': 'Order placed',
             'tag': 'e847386590ce4dBC',
             'ts': '1728004015658'},
     'lastTradeTimestamp': None,
     'lastUpdateTimestamp': None,
     'postOnly': None,
     'price': None,
     'reduceOnly': False,
     'remaining': None,
     'side': 'buy',
     'status': None,
     'stopLossPrice': None,
     'stopPrice': None,
     'symbol': 'BTC/USDT:USDT',
     'takeProfitPrice': None,
     'timeInForce': None,
     'timestamp': None,
     'trades': [],
     'triggerPrice': None,
     'type': 'limit'}
     
    {'amount': None,
     'average': None,
     'clientOrderId': 'e847386590ce4dBC143d3105bb6368c4',
     'cost': None,
     'datetime': None,
     'fee': None,
     'fees': [],
     'filled': None,
     'id': '1862325188513431552',
     'info': {'clOrdId': 'e847386590ce4dBC143d3105bb6368c4',
             'ordId': '1862325188513431552',
             'sCode': '0',
             'sMsg': '',
             'ts': '1728003495240'},
     'lastTradeTimestamp': None,
     'lastUpdateTimestamp': None,
     'postOnly': None,
     'price': None,
     'reduceOnly': False,
     'remaining': None,
     'side': None,
     'status': None,
     'stopLossPrice': None,
     'stopPrice': None,
     'symbol': 'BTC/USDT:USDT',
     'takeProfitPrice': None,
     'timeInForce': None,
     'timestamp': None,
     'trades': [],
     'triggerPrice': None,
     'type': None}
    """
    raw = res.get('info', {})
    id = res.get('id', None)
    client_order_id = res.get('clientOrderId', None)
    timestamp = raw.get('ts', None)
    symbol = res.get('symbol', None)
    type = res.get('type', None)
    side = params.get('side', None)
    price = params.get('price', None)
    average = params.get('average', None)
    amount = params.get('amount', None)
    filled = params.get('filled', None)
    remaining = res.get('remaining', None)
    cost = res.get('cost', None)
    reduce_only = res.get('reduceOnly', False)
    position_side = params.get('posSide', None)
    time_in_force = res.get('timeInForce', None)
    success = raw.get('sCode', None) == '0'
    status = params.get('status', None)
    
    return OrderResponse(
        raw = raw,
        exchange=exchange,
        id = id,
        client_order_id = client_order_id,
        timestamp=timestamp,
        symbol=symbol,
        type=type,
        side=side,
        price=price,
        average=average,
        amount=amount,
        filled=filled,
        remaining=remaining,
        cost=cost,
        reduce_only=reduce_only,
        position_side=position_side,
        time_in_force=time_in_force,
        success=success,
        status=status,
    )
    
    
def parse_private_stream(msg: Dict[str, Any]):
    if msg.get('event', None) is not None:
        return 
    if (arg := msg.get('arg', None)) is not None:
        channel = arg['channel']
        match channel:
            case "account":
                pass
            case "positions":
                pass
            case "orders":
                """
                {
                    'arg': {
                        'channel': 'orders', // channel name
                        'instType': 'ANY', // instrument type
                        'uid': '422205842008504732' // User Identifier
                    }, 
                    'data': [
                        {
                            'instType': 'SPOT', // Instrument type
                            'instId': 'BTC-USDT', // Instrument ID
                            'tgtCcy': '', // Default is `quote_ccy` for buy, `base_ccy` for sell
                            'ccy': '', // Margin currency only applicable to cross MARGIN orders in Spot and futures mode
                            'ordId': '1848670189392691200', 
                            'clOrdId': '', Client Order Id as assigned by the client
                            'algoClOrdId': '', Client supplied algo ID
                            'algoId': '', Algo ID
                            'tag': '', Order tag
                            'px': '65465.4', Price
                            'sz': '3.00708129', The Original Order quantity, `SPOT/MARGIN`, in the unit of currency; `SWAP/FUTURES/OPTION`, in the unit of contract
                            'notionalUsd': '196958.20937210717', // Estimated notional value in USD
                            'ordType': 'limit', // market, limit, post_only, fok(fill or kill order), ioc(Immediate-or-cancel order), optimal_limit_ioc, mmp(Market Maker Protection), mmp_and_post_only: Market Maker Protection and Post Only order, op_fok: Simple options (fok)
                            'side': 'sell', // order side, `buy` or `sell`
                            'posSide': '', // Position side, long or short
                            'tdMode': 'cross', // Trade mode of the order, `cross` or `isolated`   
                            'accFillSz': '0', // Accumulated filled quantity
                            'fillNotionalUsd': '', // Filled notional value in USD of the order
                            'avgPx': '0', // Average filled price
                            'state': 'live', // Order state, `canceled`, `live`, `partially_filled`, `filled`, `mmp_canceled`
                            'lever': '5', // Leverage
                            'pnl': '0', // Profit and loss
                            'feeCcy': 'USDT', // Fee Currency
                            'fee': '0', // Fee and rebate. For spot and margin, For spot and margin, it is accumulated fee charged by the platform. It is always negative, e.g. -0.01. For Expiry Futures, Perpetual Futures and Options, it is accumulated fee and rebate
                            'rebateCcy': 'BTC', // Rebate currency, if there is no rebate, this field is "".
                            'rebate': '0', // 返利
                            'category': 'normal', 
                            'uTime': '1727597064972', // update time
                            'cTime': '1727597064972', // create time
                            'source': '', 
                            'reduceOnly': 'false', 
                            'cancelSource': '', 
                            'quickMgnType': '', 
                            'stpId': '', 
                            'stpMode': 'cancel_maker', 
                            'attachAlgoClOrdId': '', 
                            'lastPx': '65464.8', 
                            'isTpLimit': 'false', 
                            'slTriggerPx': '', 
                            'slTriggerPxType': '', 
                            'tpOrdPx': '', 
                            'tpTriggerPx': '', 
                            'tpTriggerPxType': '', 
                            'slOrdPx': '', 
                            'fillPx': '', 
                            'tradeId': '', 
                            'fillSz': '0', last filled quantity
                            'fillTime': '', 
                            'fillPnl': '0', 
                            'fillFee': '0', 
                            'fillFeeCcy': '', 
                            'execType': '', 
                            'fillPxVol': '', 
                            'fillPxUsd': '', 
                            'fillMarkVol': '', 
                            'fillFwdPx': '', 
                            'fillMarkPx': '', 
                            'amendSource': '', 
                            'reqId': '', 
                            'amendResult': '', 
                            'code': '0', 
                            'msg': '', 
                            'pxType': '', 
                            'pxUsd': '', 
                            'pxVol': '', 
                            'linkedAlgoOrd': {'algoId': ''}, 
                            'attachAlgoOrds': []
                        }
                    ]
                }
                """
                pass
    
    