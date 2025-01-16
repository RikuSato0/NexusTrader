import hmac
import orjson
import hashlib
import msgspec
import asyncio
import aiohttp


from typing import Any, Dict
from urllib.parse import urljoin, urlencode

from nexustrader.base import ApiClient
from nexustrader.exchange.binance.schema import BinanceOrder, BinanceListenKey
from nexustrader.exchange.binance.constants import BinanceAccountType
from nexustrader.exchange.binance.error import BinanceClientError, BinanceServerError
from nexustrader.core.nautilius_core import hmac_signature

class BinanceApiClient(ApiClient):
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
            timeout=timeout,
        )
        self._headers = {
            "Content-Type": "application/json",
            "User-Agent": "TradingBot/1.0",
            "X-MBX-APIKEY": api_key,
        }
        self._testnet = testnet
        self._order_decoder = msgspec.json.Decoder(BinanceOrder)
        self._listen_key_decoder = msgspec.json.Decoder(BinanceListenKey)

    def _generate_signature(self, query: str) -> str:
        signature = hmac.new(
            self._secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return signature
    
    def _generate_signature_v2(self, query: str) -> str:
        signature = hmac_signature(self._secret, query)
        return signature
    
    async def _fetch(
        self,
        method: str,
        base_url: str,
        endpoint: str,
        payload: Dict[str, Any] = None,
        signed: bool = False,
    ) -> Any:
        self._init_session()
        
        url = urljoin(base_url, endpoint)
        payload = payload or {}
        payload["timestamp"] = self._clock.timestamp_ms()
        payload = urlencode(payload)

        if signed:
            signature = self._generate_signature_v2(payload)
            payload += f"&signature={signature}"

        url += f"?{payload}"
        self._log.debug(f"Request: {url}")

        try:
            response = await self._session.request(
                method=method,
                url=url,
                headers=self._headers,
            )
            raw = await response.read()
            self.raise_error(raw, response.status, response.headers)
            return raw
        except aiohttp.ClientError as e:
            self._log.error(f"Client Error {method} Url: {url} {e}")
            raise
        except asyncio.TimeoutError:
            self._log.error(f"Timeout {method} Url: {url}")
            raise
        except Exception as e:
            self._log.error(f"Error {method} Url: {url} {e}")
            raise

    def raise_error(self, raw: bytes, status: int, headers: Dict[str, Any]):
        if 400 <= status < 500:
            raise BinanceClientError(status, orjson.loads(raw), headers)
        elif status >= 500:
            raise BinanceServerError(status, orjson.loads(raw), headers)

    def _get_base_url(self, account_type: BinanceAccountType) -> str:
        if account_type == BinanceAccountType.SPOT:
            if self._testnet:
                return BinanceAccountType.SPOT_TESTNET.base_url
            return BinanceAccountType.SPOT.base_url
        elif account_type == BinanceAccountType.MARGIN:
            return BinanceAccountType.MARGIN.base_url
        elif account_type == BinanceAccountType.ISOLATED_MARGIN:
            return BinanceAccountType.ISOLATED_MARGIN.base_url
        elif account_type == BinanceAccountType.USD_M_FUTURE:
            if self._testnet:
                return BinanceAccountType.USD_M_FUTURE_TESTNET.base_url
            return BinanceAccountType.USD_M_FUTURE.base_url
        elif account_type == BinanceAccountType.COIN_M_FUTURE:
            if self._testnet:
                return BinanceAccountType.COIN_M_FUTURE_TESTNET.base_url
            return BinanceAccountType.COIN_M_FUTURE.base_url
        elif account_type == BinanceAccountType.PORTFOLIO_MARGIN:
            return BinanceAccountType.PORTFOLIO_MARGIN.base_url

    async def put_dapi_v1_listen_key(self):
        """
        https://developers.binance.com/docs/derivatives/coin-margined-futures/user-data-streams/Keepalive-User-Data-Stream
        """
        base_url = self._get_base_url(BinanceAccountType.COIN_M_FUTURE)
        end_point = "/dapi/v1/listenKey"
        raw = await self._fetch("PUT", base_url, end_point)
        return orjson.loads(raw)

    async def post_dapi_v1_listen_key(self):
        """
        https://developers.binance.com/docs/derivatives/coin-margined-futures/user-data-streams/Start-User-Data-Stream
        """
        base_url = self._get_base_url(BinanceAccountType.COIN_M_FUTURE)
        end_point = "/dapi/v1/listenKey"
        raw = await self._fetch("POST", base_url, end_point)
        return self._listen_key_decoder.decode(raw)

    async def post_api_v3_user_data_stream(self) -> BinanceListenKey:
        """
        https://developers.binance.com/docs/binance-spot-api-docs/user-data-stream#create-a-listenkey-user_stream
        """
        base_url = self._get_base_url(BinanceAccountType.SPOT)
        end_point = "/api/v3/userDataStream"
        raw = await self._fetch("POST", base_url, end_point)
        return self._listen_key_decoder.decode(raw)

    async def put_api_v3_user_data_stream(self, listen_key: str):
        """
        https://developers.binance.com/docs/binance-spot-api-docs/user-data-stream
        """
        base_url = self._get_base_url(BinanceAccountType.SPOT)
        end_point = "/api/v3/userDataStream"
        raw = await self._fetch(
            "PUT", base_url, end_point, payload={"listenKey": listen_key}
        )
        return orjson.loads(raw)

    async def post_sapi_v1_user_data_stream(self) -> BinanceListenKey:
        """
        https://developers.binance.com/docs/margin_trading/trade-data-stream/Start-Margin-User-Data-Stream
        """
        base_url = self._get_base_url(BinanceAccountType.MARGIN)
        end_point = "/sapi/v1/userDataStream"
        raw = await self._fetch("POST", base_url, end_point)
        return self._listen_key_decoder.decode(raw)

    async def put_sapi_v1_user_data_stream(self, listen_key: str):
        """
        https://developers.binance.com/docs/margin_trading/trade-data-stream/Keepalive-Margin-User-Data-Stream
        """
        base_url = self._get_base_url(BinanceAccountType.MARGIN)
        end_point = "/sapi/v1/userDataStream"
        raw = await self._fetch(
            "PUT", base_url, end_point, payload={"listenKey": listen_key}
        )
        return orjson.loads(raw)

    async def post_sapi_v1_user_data_stream_isolated(self, symbol: str) -> BinanceListenKey:
        """
        https://developers.binance.com/docs/margin_trading/trade-data-stream/Start-Isolated-Margin-User-Data-Stream
        """
        base_url = self._get_base_url(BinanceAccountType.ISOLATED_MARGIN)
        end_point = "/sapi/v1/userDataStream/isolated"
        raw = await self._fetch("POST", base_url, end_point, payload={"symbol": symbol})
        return self._listen_key_decoder.decode(raw)

    async def put_sapi_v1_user_data_stream_isolated(self, symbol: str, listen_key: str):
        """
        https://developers.binance.com/docs/margin_trading/trade-data-stream/Keepalive-Isolated-Margin-User-Data-Stream
        """
        base_url = self._get_base_url(BinanceAccountType.ISOLATED_MARGIN)
        end_point = "/sapi/v1/userDataStream/isolated"
        raw = await self._fetch(
            "PUT",
            base_url,
            end_point,
            payload={"symbol": symbol, "listenKey": listen_key},
        )
        return orjson.loads(raw)

    async def post_fapi_v1_listen_key(self) -> BinanceListenKey:
        """
        https://developers.binance.com/docs/derivatives/usds-margined-futures/user-data-streams/Start-User-Data-Stream
        """
        base_url = self._get_base_url(BinanceAccountType.USD_M_FUTURE)
        end_point = "/fapi/v1/listenKey"
        raw = await self._fetch("POST", base_url, end_point)
        return self._listen_key_decoder.decode(raw)

    async def put_fapi_v1_listen_key(self):
        """
        https://developers.binance.com/docs/derivatives/usds-margined-futures/user-data-streams/Keepalive-User-Data-Stream
        """
        base_url = self._get_base_url(BinanceAccountType.USD_M_FUTURE)
        end_point = "/fapi/v1/listenKey"
        raw = await self._fetch("PUT", base_url, end_point)
        return orjson.loads(raw)

    async def post_papi_v1_listen_key(self) -> BinanceListenKey:
        """
        https://developers.binance.com/docs/derivatives/portfolio-margin/user-data-streams/Start-User-Data-Stream
        """
        base_url = self._get_base_url(BinanceAccountType.PORTFOLIO_MARGIN)
        end_point = "/papi/v1/listenKey"
        raw = await self._fetch("POST", base_url, end_point)
        return self._listen_key_decoder.decode(raw)

    async def put_papi_v1_listen_key(self):
        """
        https://developers.binance.com/docs/derivatives/portfolio-margin/user-data-streams/Keepalive-User-Data-Stream
        """
        base_url = self._get_base_url(BinanceAccountType.PORTFOLIO_MARGIN)
        end_point = "/papi/v1/listenKey"
        raw = await self._fetch("PUT", base_url, end_point)
        return orjson.loads(raw)

    async def post_sapi_v1_margin_order(
        self,
        symbol: str,
        side: str,
        type: str,
        **kwargs,
    ) -> BinanceOrder:
        """
        https://developers.binance.com/docs/margin_trading/trade/Margin-Account-New-Order
        """
        base_url = self._get_base_url(BinanceAccountType.MARGIN)
        end_point = "/sapi/v1/margin/order"
        data = {
            "symbol": symbol,
            "side": side,
            "type": type,
            **kwargs,
        }
        raw = await self._fetch("POST", base_url, end_point, payload=data, signed=True)
        return self._order_decoder.decode(raw)

    async def post_api_v3_order(
        self,
        symbol: str,
        side: str,
        type: str,
        **kwargs,
    ) -> BinanceOrder:
        """
        https://developers.binance.com/docs/binance-spot-api-docs/rest-api/public-api-endpoints#new-order-trade
        """
        base_url = self._get_base_url(BinanceAccountType.SPOT)
        end_point = "/api/v3/order"
        data = {
            "symbol": symbol,
            "side": side,
            "type": type,
            **kwargs,
        }
        raw = await self._fetch("POST", base_url, end_point, payload=data, signed=True)
        return self._order_decoder.decode(raw)

    async def post_fapi_v1_order(
        self,
        symbol: str,
        side: str,
        type: str,
        **kwargs,
    ) -> BinanceOrder:
        """
        https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api
        """
        base_url = self._get_base_url(BinanceAccountType.USD_M_FUTURE)
        end_point = "/fapi/v1/order"
        data = {
            "symbol": symbol,
            "side": side,
            "type": type,
            **kwargs,
        }
        raw = await self._fetch("POST", base_url, end_point, payload=data, signed=True)
        return self._order_decoder.decode(raw)

    async def post_dapi_v1_order(
        self,
        symbol: str,
        side: str,
        type: str,
        **kwargs,
    ) -> BinanceOrder:
        """
        https://developers.binance.com/docs/derivatives/coin-margined-futures/trade
        """
        base_url = self._get_base_url(BinanceAccountType.COIN_M_FUTURE)
        end_point = "/dapi/v1/order"
        data = {
            "symbol": symbol,
            "side": side,
            "type": type,
            **kwargs,
        }
        raw = await self._fetch("POST", base_url, end_point, payload=data, signed=True)
        return self._order_decoder.decode(raw)

    async def post_papi_v1_um_order(
        self,
        symbol: str,
        side: str,
        type: str,
        **kwargs,
    ) -> BinanceOrder:
        """
        https://developers.binance.com/docs/derivatives/portfolio-margin/trade
        """
        base_url = self._get_base_url(BinanceAccountType.PORTFOLIO_MARGIN)
        end_point = "/papi/v1/um/order"

        data = {
            "symbol": symbol,
            "side": side,
            "type": type,
            **kwargs,
        }
        raw = await self._fetch("POST", base_url, end_point, payload=data, signed=True)
        return self._order_decoder.decode(raw)

    async def post_papi_v1_cm_order(
        self,
        symbol: str,
        side: str,
        type: str,
        **kwargs,
    ) -> BinanceOrder:
        """
        https://developers.binance.com/docs/derivatives/portfolio-margin/trade/New-CM-Order
        """
        base_url = self._get_base_url(BinanceAccountType.PORTFOLIO_MARGIN)
        end_point = "/papi/v1/cm/order"

        data = {
            "symbol": symbol,
            "side": side,
            "type": type,
            **kwargs,
        }
        raw = await self._fetch("POST", base_url, end_point, payload=data, signed=True)
        return self._order_decoder.decode(raw)

    async def post_papi_v1_margin_order(
        self,
        symbol: str,
        side: str,
        type: str,
        **kwargs,
    ) -> BinanceOrder:
        """
        https://developers.binance.com/docs/derivatives/portfolio-margin/trade/New-Margin-Order
        """
        base_url = self._get_base_url(BinanceAccountType.PORTFOLIO_MARGIN)
        end_point = "/papi/v1/margin/order"

        data = {
            "symbol": symbol,
            "side": side,
            "type": type,
            **kwargs,
        }
        raw = await self._fetch("POST", base_url, end_point, payload=data, signed=True)
        return self._order_decoder.decode(raw)
    
    async def delete_api_v3_order(self, symbol: str, order_id: int, **kwargs) -> BinanceOrder:
        """
        https://developers.binance.com/docs/binance-spot-api-docs/rest-api/public-api-endpoints#cancel-order-trade
        """
        base_url = self._get_base_url(BinanceAccountType.SPOT)
        end_point = "/api/v3/order"
        data = {
            "symbol": symbol,
            "orderId": order_id,
            **kwargs,
        }
        raw = await self._fetch("DELETE", base_url, end_point, payload=data, signed=True)
        return self._order_decoder.decode(raw)

    async def delete_sapi_v1_margin_order(self, symbol: str, order_id: int, **kwargs) -> BinanceOrder:
        """
        https://developers.binance.com/docs/margin_trading/trade/Margin-Account-Cancel-Order
        """
        base_url = self._get_base_url(BinanceAccountType.MARGIN)
        end_point = "/sapi/v1/margin/order"
        data = {
            "symbol": symbol,
            "orderId": order_id,
            **kwargs,
        }
        raw = await self._fetch("DELETE", base_url, end_point, payload=data, signed=True)
        return self._order_decoder.decode(raw)

    async def delete_fapi_v1_order(self, symbol: str, order_id: int, **kwargs) -> BinanceOrder:
        """
        https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Cancel-Order
        """
        base_url = self._get_base_url(BinanceAccountType.USD_M_FUTURE)
        end_point = "/fapi/v1/order"
        data = {
            "symbol": symbol,
            "orderId": order_id,
            **kwargs,
        }
        raw = await self._fetch("DELETE", base_url, end_point, payload=data, signed=True)
        return self._order_decoder.decode(raw)

    async def delete_dapi_v1_order(self, symbol: str, order_id: int, **kwargs) -> BinanceOrder:
        """
        https://developers.binance.com/docs/derivatives/coin-margined-futures/trade/Cancel-Order
        """
        base_url = self._get_base_url(BinanceAccountType.COIN_M_FUTURE)
        end_point = "/dapi/v1/order"
        data = {
            "symbol": symbol,
            "orderId": order_id,
            **kwargs,
        }
        raw = await self._fetch("DELETE", base_url, end_point, payload=data, signed=True)
        return self._order_decoder.decode(raw)

    async def delete_papi_v1_um_order(self, symbol: str, order_id: int, **kwargs) -> BinanceOrder:
        """
        https://developers.binance.com/docs/derivatives/portfolio-margin/trade/Cancel-UM-Order
        """
        base_url = self._get_base_url(BinanceAccountType.PORTFOLIO_MARGIN)
        end_point = "/papi/v1/um/order"
        data = {
            "symbol": symbol,
            "orderId": order_id,
            **kwargs,
        }
        raw = await self._fetch("DELETE", base_url, end_point, payload=data, signed=True)
        return self._order_decoder.decode(raw)

    async def delete_papi_v1_cm_order(self, symbol: str, order_id: int, **kwargs) -> BinanceOrder:
        """
        https://developers.binance.com/docs/derivatives/portfolio-margin/trade/Cancel-CM-Order
        """
        base_url = self._get_base_url(BinanceAccountType.PORTFOLIO_MARGIN)
        end_point = "/papi/v1/cm/order"
        data = {
            "symbol": symbol,
            "orderId": order_id,
            **kwargs,
        }
        raw = await self._fetch("DELETE", base_url, end_point, payload=data, signed=True)
        return self._order_decoder.decode(raw)
    
    async def delete_papi_v1_margin_order(self, symbol: str, order_id: int, **kwargs) -> BinanceOrder:
        """
        https://developers.binance.com/docs/derivatives/portfolio-margin/trade/Cancel-Margin-Account-Order
        """
        base_url = self._get_base_url(BinanceAccountType.PORTFOLIO_MARGIN)
        end_point = "/papi/v1/margin/order"
        data = {
            "symbol": symbol,
            "orderId": order_id,
            **kwargs,
        }
        raw = await self._fetch("DELETE", base_url, end_point, payload=data, signed=True)
        return self._order_decoder.decode(raw)
