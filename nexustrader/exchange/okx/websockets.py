import time
import hmac
import base64
import asyncio

from typing import Literal
from typing import Any
from typing import Callable
from typing import Dict
from aiolimiter import AsyncLimiter

from nexustrader.base import WSClient
from nexustrader.exchange.okx.constants import OkxAccountType, OkxKlineInterval
from nexustrader.core.entity import TaskManager

class OkxWSClient(WSClient):
    def __init__(
        self,
        account_type: OkxAccountType,
        handler: Callable[..., Any],
        task_manager: TaskManager,
        api_key: str | None = None,
        secret: str | None = None,
        passphrase: str | None = None,
        business_url: bool = False,
    ):
        self._api_key = api_key
        self._secret = secret
        self._passphrase = passphrase
        self._account_type = account_type
        self._authed = False
        self._business_url = business_url
        if self.is_private:
            url = f"{account_type.stream_url}/v5/private"
        else:
            if business_url:
                url = f"{account_type.stream_url}/v5/business"
            else:
                url = f"{account_type.stream_url}/v5/public"
        
        super().__init__(
            url,
            limiter=AsyncLimiter(max_rate=2, time_period=1),
            handler=handler,
            task_manager=task_manager,
            specific_ping_msg=b"ping",
            ping_idle_timeout=5,
            ping_reply_timeout=2,
        )

    @property
    def is_private(self):
        return (
            self._api_key is not None
            or self._secret is not None
            or self._passphrase is not None
        )

    def _get_auth_payload(self):
        timestamp = int(time.time())
        message = str(timestamp) + "GET" + "/users/self/verify"
        mac = hmac.new(
            bytes(self._secret, encoding="utf8"),
            bytes(message, encoding="utf-8"),
            digestmod="sha256",
        )
        d = mac.digest()
        sign = base64.b64encode(d)
        if self._api_key is None or self._passphrase is None or self._secret is None:
            raise ValueError("API Key, Passphrase, or Secret is missing.")
        arg = {
            "apiKey": self._api_key,
            "passphrase": self._passphrase,
            "timestamp": timestamp,
            "sign": sign.decode("utf-8"),
        }
        payload = {"op": "login", "args": [arg]}
        return payload

    async def _auth(self):
        if not self._authed:
            await self._send(self._get_auth_payload())
            self._authed = True
            await asyncio.sleep(5)
    
    async def _submit(self, op: str, params: Dict[str, Any]):
        await self.connect()
        await self._auth()
        
        payload = {
            "id": self._clock.timestamp_ms(),
            "op": op,
            "args": [params],
        }
        await self._send(payload)

    async def _subscribe(self, params: Dict[str, Any], subscription_id: str, auth: bool = False):
        if subscription_id not in self._subscriptions:
            await self.connect()

            if auth:
                await self._auth()

            payload = {
                "op": "subscribe",
                "args": [params],
            }
            
            self._subscriptions[subscription_id] = payload
            await self._send(payload)
        else:
            print(f"Already subscribed to {subscription_id}")
    
    async def place_order(self, inst_id: str, td_mode: str, side: str, ord_type: str, sz: str, **kwargs):
        params = {
            "instId": inst_id,
            "tdMode": td_mode,
            "side": side,
            "ordType": ord_type,
            "sz": sz,
            **kwargs,
        }
        await self._submit("order", params)
    
    async def cancel_order(self, inst_id: str, ord_id: str | None = None, cl_ord_id: str | None = None):
        params = {
            "instId": inst_id,
        }
        if ord_id:
            params["ordId"] = ord_id
        if cl_ord_id:
            params["clOrdId"] = cl_ord_id
        await self._submit("cancel-order", params)
        

    async def subscribe_order_book(
        self,
        symbol: str,
        channel: Literal[
            "books", "books5", "bbo-tbt", "books-l2-tbt", "books50-l2-tbt"
        ],
    ):
        """
        https://www.okx.com/docs-v5/en/#order-book-trading-market-data-ws-order-book-channel
        """
        params = {"channel": channel, "instId": symbol}
        subscription_id = f"{channel}.{symbol}"
        await self._subscribe(params, subscription_id)

    async def subscribe_trade(self, symbol: str):
        """
        https://www.okx.com/docs-v5/en/#order-book-trading-market-data-ws-all-trades-channel
        """
        params = {"channel": "trades", "instId": symbol}
        subscription_id = f"trade.{symbol}"
        await self._subscribe(params, subscription_id)

    async def subscribe_candlesticks(
        self,
        symbol: str,
        interval: OkxKlineInterval,
    ):
        """
        https://www.okx.com/docs-v5/en/#order-book-trading-market-data-ws-candlesticks-channel
        """
        if not self._business_url:
            raise ValueError("candlesticks are only supported on business url")
        channel = interval.value
        params = {"channel": channel, "instId": symbol}
        subscription_id = f"{channel}.{symbol}"
        await self._subscribe(params, subscription_id)

    async def subscribe_account(self):
        params = {"channel": "account"}
        subscription_id = "account"
        await self._subscribe(params, subscription_id, auth=True)

    async def subscribe_account_position(self):
        params = {"channel": "balance_and_position"}
        subscription_id = "account_position"
        await self._subscribe(params, subscription_id, auth=True)

    async def subscribe_positions(
        self, inst_type: Literal["MARGIN", "SWAP", "FUTURES", "OPTION", "ANY"] = "ANY"
    ):
        subscription_id = f"position.{inst_type}"
        params = {"channel": "positions", "instType": inst_type}
        await self._subscribe(params, subscription_id, auth=True)

    async def subscribe_orders(
        self, inst_type: Literal["MARGIN", "SWAP", "FUTURES", "OPTION", "ANY"] = "ANY"
    ):
        subscription_id = f"orders.{inst_type}"
        params = {"channel": "orders", "instType": inst_type}
        await self._subscribe(params, subscription_id, auth=True)

    async def subscribe_fills(self):
        subscription_id = "fills"
        params = {"channel": "fills"}
        await self._subscribe(params, subscription_id, auth=True)

    async def _resubscribe(self):
        if self.is_private:
            self._authed = False
            await self._auth()
        for _, payload in self._subscriptions.items():
            await self._send(payload)
