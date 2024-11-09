import hmac
import hashlib
import aiohttp
import asyncio
import msgspec
import orjson
from typing import Any, Dict, List
from urllib.parse import urljoin, urlencode

from tradebot.base import ApiClient
from tradebot.exchange.bybit.error import BybitError
from tradebot.exchange.bybit.types import BybitResponse

class BybitApiClient(ApiClient):
    def __init__(
        self,
        api_key: str = None,
        secret: str = None,
        testnet: bool = False,
        timeout: int = 10,
    ):
        super().__init__(
            api_key=api_key,
            secret=secret,
            testnet=testnet,
            timeout=timeout,
        )
        self._recv_window = 5000
        self._testnet = testnet
        
        self._headers = {
            "Content-Type": "application/json",
            "User-Agent": "TradingBot/1.0",
            "X-BAPI-API-KEY": api_key,
        }
        
        self._response_decoder = msgspec.json.Decoder(BybitResponse)
        

    def _generate_signature(self, payload: str) -> List[str]:
        timestamp = str(self._clock.timestamp_ms())

        param = str(timestamp) + self._api_key + str(self._recv_window) + payload
        hash = hmac.new(
            bytes(self.secret_key, "utf-8"), param.encode("utf-8"), hashlib.sha256
        )
        signature = hash.hexdigest()
        return [signature, timestamp]
    
    async def _fetch(
        self,
        method: str,
        base_url: str,
        endpoint: str,
        payload: Dict[str, Any] = None,
        signed: bool = False,
    ):
        url = urljoin(base_url, endpoint)
        payload = payload or {}
        
        payload_str = (
            urlencode(payload) if method == "GET" 
            else orjson.dumps(payload).encode("utf-8")
        )

        headers = self._headers
        if signed:
            signature, timestamp = self._generate_signature(payload_str)
            headers = {
                **headers,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-SIGN": signature, 
                "X-BAPI-RECV-WINDOW": str(self._recv_window),
            }

        if method == "GET":
            url += f"?{payload_str}"
            payload_str = None
        
        try:
            self._log.debug(f"Request: {url} {payload_str}")
            response = await self._session.request(
                method=method,
                url=url,
                headers=headers,
                data=payload_str,
            )
            raw = await response.read()
            if response.status >= 400:
                raise BybitError(
                    code=response.status,
                    message=orjson.loads(raw) if raw else None,
                )
            bybit_response: BybitResponse = self._response_decoder.decode(raw)
            if bybit_response.retCode == 0:
                return raw
            else:
                raise BybitError(
                    code=bybit_response.retCode,
                    message=bybit_response.retMsg,
                )
        except aiohttp.ClientError as e:
            self._log.error(f"Client Error {method} Url: {url} {e}")
            raise
        except asyncio.TimeoutError:
            self._log.error(f"Timeout {method} Url: {url}")
            raise
        except Exception as e:
            self._log.error(f"Error {method} Url: {url} {e}")
            raise

