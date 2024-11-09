from tradebot.base import ApiClient
from tradebot.exchange.okx import OkxAccountType
import msgspec
from tradebot.exchange.okx.types import (
    OKXPlaceOrderResponse,
    OKXCancelOrderResponse,
)
from typing import Dict, Any
import orjson
from tradebot.exchange.okx.error import OKXHttpError
import time
import hmac
import base64


class OkxApiClient(ApiClient):
    def __init__(
        self,
        api_key: str = None,
        secret: str = None,
        passphrase: str = None,
        testnet: bool = False,
        timeout: int = 10,
    ):
        super().__init__(
            api_key=api_key,
            secret=secret,
            timeout=timeout,
        )
        self._base_url = "https://aws.okx.com" if testnet else "https://www.okx.com"
        self._passphrase = passphrase
        self._testnet = testnet
        self._place_order_decoder = msgspec.json.Decoder(OKXPlaceOrderResponse)
        self._cancel_order_decoder = msgspec.json.Decoder(OKXCancelOrderResponse)

    def raise_error(self, raw: bytes, status: int, headers: Dict[str, Any]):
        if 400 <= status < 500:
            raise OKXHttpError(status, orjson.loads(raw), headers)
        elif status >= 500:
            raise OKXHttpError(status, orjson.loads(raw), headers)

    async def place_order(
        self, instId: str, tdMode: str, side: str, ordType: str, sz: str, **kwargs
    ) -> OKXPlaceOrderResponse:
        """
        Place a new order
        https://www.okx.com/docs-v5/en/#rest-api-trade-place-order
        """
        endpoint = "/api/v5/trade/order"
        payload = {
            "instId": instId,
            "tdMode": tdMode,
            "side": side,
            "ordType": ordType,
            "sz": sz,
            **kwargs,
        }
        raw = await self._fetch(
            "POST", self._base_url, endpoint, payload=payload, signed=True
        )
        return self._place_order_decoder.decode(raw)

    async def cancel_order(
        self, instId: str, ordId: str = None, clOrdId: str = None
    ) -> OKXCancelOrderResponse:
        """
        Cancel an existing order
        https://www.okx.com/docs-v5/en/#rest-api-trade-cancel-order
        """
        endpoint = "/api/v5/trade/cancel-order"
        payload = {"instId": instId}
        if ordId:
            payload["ordId"] = ordId
        if clOrdId:
            payload["clOrdId"] = clOrdId

        raw = await self._fetch(
            "POST", self._base_url, endpoint, payload=payload, signed=True
        )
        return self._cancel_order_decoder.decode(raw)

    async def _fetch(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any] = None,
        payload: Dict[str, Any] = None,
        signed: bool = False,
    ) -> bytes:
        """
        发送HTTP请求到OKX API
        """
        url = f"{self._base_url}{endpoint}"
        
        request_path = endpoint
        if params:
            query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            request_path = f"{endpoint}?{query_string}"
            url = f"{url}?{query_string}"

        headers = {
            "Content-Type": "application/json",
        }

        if signed and self._api_key:
            timestamp = str(int(time.time() * 1000))
            # 根据OKX要求构建签名字符串
            body = ''
            if payload:
                body = orjson.dumps(payload).decode()
            
            # 签名字符串格式: timestamp + method + requestPath + body
            sign_str = f"{timestamp}{method}{request_path}{body}"
            signature = self._generate_signature(sign_str)

            headers.update({
                "OK-ACCESS-KEY": self._api_key,
                "OK-ACCESS-SIGN": signature,
                "OK-ACCESS-TIMESTAMP": timestamp,
                "OK-ACCESS-PASSPHRASE": self._passphrase,
            })
            
            # 如果是测试网，需要添加模拟盘的header
            if self._testnet:
                headers["x-simulated-trading"] = "1"

        return await self.request(
            method=method,
            url=url,
            headers=headers,
            data=orjson.dumps(payload) if payload else None
        )

    def _generate_signature(self, message: str) -> str:
        """
        生成OKX API签名
        使用HMAC SHA256算法，然后进行Base64编码
        """
        mac = hmac.new(
            bytes(self._secret, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        return base64.b64encode(mac.digest()).decode()

