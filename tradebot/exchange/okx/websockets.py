import time
import hmac
import base64
import asyncio

from typing import Literal
from typing import Any, Dict
from decimal import Decimal
from typing import Callable

from asynciolimiter import Limiter


from tradebot.types import (
    BookL1,
    Trade,
)
from tradebot.entity import EventSystem
from tradebot.base import WSClient
from tradebot.constants import EventType


from tradebot.exchange.okx.constants import STREAM_URLS
from tradebot.exchange.okx.constants import OkxAccountType


class OkxWSClient(WSClient):
    def __init__(
        self,
        account_type: OkxAccountType,
        handler: Callable[..., Any],
        api_key: str = None,
        secret: str = None,
        passphrase: str = None,
    ):
        self._api_key = api_key
        self._secret = secret
        self._passphrase = passphrase
        self._account_type = account_type
        if self.is_private:
            url = f"{STREAM_URLS[account_type]}/v5/private"
            self._authed = False
        else:
            url = f"{STREAM_URLS[account_type]}/v5/public"
        super().__init__(url, limiter=Limiter(2 / 1), handler=handler)

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

    async def _subscribe(self, params: dict, subscription_id: str, auth: bool = False):
        if subscription_id not in self._subscriptions:
            await self.connect()
            await self._limiter.wait()

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
        interval: Literal[
            "1s",
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "1H",
            "2H",
            "4H",
            "6H",
            "12H",
            "1D",
            "1W",
            "1M",
        ],
    ):
        """
        https://www.okx.com/docs-v5/en/#order-book-trading-market-data-ws-candlesticks-channel
        """
        channel = f"candle{interval}"
        params = {"channel": channel, "instId": symbol}
        subscription_id = f"{channel}.{symbol}"
        await self._subscribe(params, subscription_id)

    async def subscribe_account(self):
        params = {"channel": "account"}
        subscription_id = "account"
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

    async def subscrbe_fills(self):
        subscription_id = "fills"
        params = {"channel": "fills"}
        await self._subscribe(params, subscription_id, auth=True)

    async def _resubscribe(self):
        if self.is_private:
            self._authed = False
            await self._auth()
        for _, payload in self._subscriptions.items():
            await self._limiter.wait()
            await self._send(payload)
