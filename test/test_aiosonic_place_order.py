from abc import ABC, abstractmethod
from typing import Dict, Any, Literal
from decimal import Decimal
from asynciolimiter import Limiter
from tradebot.base import AsyncHttpRequests, WSClient
from tradebot.entity import Order
import asyncio


import hmac
import base64
import time
from typing import Dict, Any, Literal
from decimal import Decimal

# from tradebot.exchanges.base import ExchangeInterface
from tradebot.entity import Order
from tradebot.constants import CONFIG

OKX_API_KEY = CONFIG["okex_demo"]["API_KEY"]
OKX_SECRET = CONFIG["okex_demo"]["SECRET"]
OKX_PASSPHRASE = CONFIG["okex_demo"]["PASSPHRASE"]


class ExchangeInterface(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config["api_key"]
        self.secret = config["secret"]
        self.base_url = config["base_url"]
        self.ws_url = config["ws_url"]
        self.rate_limit = config.get("rate_limit", 10)
        self.limiter = Limiter(rate_limit=self.rate_limit)
        self.http_client = AsyncHttpRequests()
        self.ws_manager = None  # Will be initialized in connect_ws method

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        order_type: Literal["market", "limit"],
        amount: Decimal,
        price: Decimal = None,
        params: Dict[str, Any] = None,
    ) -> Order:
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def place_order_ws(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        order_type: Literal["market", "limit"],
        amount: Decimal,
        price: Decimal = None,
        params: Dict[str, Any] = None,
    ) -> Order:
        pass

    @abstractmethod
    async def cancel_order_ws(self, order_id: str, symbol: str) -> Dict[str, Any]:
        pass

    async def connect_ws(self):
        self.ws_manager = WSClient(self.ws_url, self.limiter)
        await self.ws_manager.connect()

    async def disconnect_ws(self):
        if self.ws_manager:
            self.ws_manager.disconnect()

    @abstractmethod
    def sign_request(
        self, method: str, endpoint: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        pass


class OKXExchange(ExchangeInterface):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.passphrase = config["passphrase"]

    async def place_order(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        order_type: Literal["market", "limit"],
        amount: Decimal,
        price: Decimal = None,
        params: Dict[str, Any] = None,
    ) -> Order:
        await self.limiter.wait()
        endpoint = "/api/v5/trade/order"
        data = {
            "instId": symbol,
            "tdMode": "cash",
            "side": side,
            "ordType": order_type,
            "sz": str(amount),
        }
        if order_type == "limit":
            data["px"] = str(price)
        if params:
            data.update(params)

        headers = self.sign_request("POST", endpoint, data)
        response = await self.http_client.post(
            f"{self.base_url}{endpoint}", json=data, headers=headers
        )
        return self._parse_order_response(response)

    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        await self.limiter.wait()
        endpoint = "/api/v5/trade/cancel-order"
        data = {
            "instId": symbol,
            "ordId": order_id,
        }
        headers = self.sign_request("POST", endpoint, data)
        response = await self.http_client.post(
            f"{self.base_url}{endpoint}", json=data, headers=headers
        )
        return response

    async def place_order_ws(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        order_type: Literal["market", "limit"],
        amount: Decimal,
        price: Decimal = None,
        params: Dict[str, Any] = None,
    ) -> Order:
        await self.limiter.wait()
        data = {
            "id": str(int(time.time() * 1000)),
            "op": "order",
            "args": [
                {
                    "instId": symbol,
                    "tdMode": "cash",
                    "side": side,
                    "ordType": order_type,
                    "sz": str(amount),
                }
            ],
        }
        if order_type == "limit":
            data["args"][0]["px"] = str(price)
        if params:
            data["args"][0].update(params)

        self.ws_manager._send(data)
        response = await self._wait_for_ws_response(data["id"])
        return self._parse_order_response(response)

    async def cancel_order_ws(self, order_id: str, symbol: str) -> Dict[str, Any]:
        await self.limiter.wait()
        data = {
            "id": str(int(time.time() * 1000)),
            "op": "cancel-order",
            "args": [
                {
                    "instId": symbol,
                    "ordId": order_id,
                }
            ],
        }
        self.ws_manager._send(data)
        return await self._wait_for_ws_response(data["id"])

    def sign_request(
        self, method: str, endpoint: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        timestamp = str(int(time.time() * 1000))
        message = (
            timestamp + method + endpoint + ("" if params is None else str(params))
        )
        signature = base64.b64encode(
            hmac.new(
                self.secret.encode("utf-8"), message.encode("utf-8"), digestmod="sha256"
            ).digest()
        ).decode("utf-8")

        return {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
        }

    def _parse_order_response(self, response: Dict[str, Any]) -> Order:
        # TBD
        return Order(response)

    async def _wait_for_ws_response(self, request_id: str) -> Dict[str, Any]:
        # Implement logic to wait for and return the WebSocket response
        pass


async def main():
    exchange = OKXExchange(
        {
            "api_key": OKX_API_KEY,
            "secret": OKX_SECRET,
            "passphrase": OKX_PASSPHRASE,
            "base_url": "https://www.okex.com",
            "ws_url": "wss://www.okex.com/ws/v5",
        }
    )
    order = await exchange.place_order(
        symbol="BTC-USDT",
        side="buy",
        order_type="limit",
        amount=Decimal("0.001"),
        price=Decimal("30000"),
    )
    print(order)


if __name__ == "__main__":
    asyncio.run(main())
