import time
import hmac
import hashlib
import ccxt

from typing import Any, Dict
from urllib.parse import urljoin


from tradebot.base import RestApi
from tradebot.exchange.binance.constants import BASE_URLS, ENDPOINTS
from tradebot.exchange.binance.constants import AccountType, EndpointsType


class BinanceRestApi(RestApi):
    @property
    def market(self) -> Dict[str, Any]:
        return self._market

    @property
    def market_id(self) -> Dict[str, Any]:
        return self._market_id

    def __init__(
        self,
        account_type: AccountType,
        api_key: str = None,
        secret: str = None,
        **kwargs,
    ):
        self._api_key = api_key
        self._secret = secret
        self._account_type = account_type
        self._base_url = BASE_URLS[account_type]
        self._market = self._load_markets(account_type)
        self._market_id = self._load_market_id()
        super().__init__(**kwargs)

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
        }
        if self._api_key:
            headers["X-MBX-APIKEY"] = self._api_key
        return headers

    def _generate_signature(self, query: str) -> str:
        signature = hmac.new(
            self._secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return signature

    async def _fetch(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any] = {},
        data: Dict[str, Any] = {},
        signed: bool = False,
    ) -> Any:
        url = urljoin(self._base_url, endpoint)

        data["timestamp"] = time.time_ns() // 1_000_000
        query = "&".join([f"{k}={v}" for k, v in data.items()])
        headers = self._get_headers()

        if signed:
            signature = self._generate_signature(query)
            params["signature"] = signature

        return await self.request(
            method, url, params=params, data=data, headers=headers
        )

    async def start_user_data_stream(self) -> Dict[str, Any]:
        if self._api_key is None:
            raise ValueError("API key is required to start user data stream")
        endpoint = self._generate_endpoint(EndpointsType.USER_DATA_STREAM)
        return await self._fetch("POST", endpoint)

    async def keep_alive_user_data_stream(self, listen_key: str) -> Dict[str, Any]:
        if self._api_key is None:
            raise ValueError("API key is required to keep alive user data stream")
        endpoint = self._generate_endpoint(EndpointsType.USER_DATA_STREAM)
        return await self._fetch("PUT", endpoint, params={"listenKey": listen_key})

    async def new_order(self, symbol: str, side: str, type: str, **kwargs):
        endpoint = self._generate_endpoint(EndpointsType.TRADING)
        endpoint = f"{endpoint}/order"
        params = {"symbol": symbol, "side": side, "type": type, **kwargs}
        return await self._fetch("POST", endpoint, data=params, signed=True)

    def _generate_endpoint(self, endpoint_type: EndpointsType) -> str:
        return ENDPOINTS[endpoint_type][self._account_type]

    def _load_markets(self, account_type: AccountType):
        spot_markets = {}
        usdm_markets = {}
        coinm_markets = {}
        market = ccxt.binance().load_markets()
        for symbol, data in market.items():
            if data["spot"]:
                spot_markets[symbol] = data
            elif data["linear"]:
                usdm_markets[symbol] = data
            elif data["inverse"]:
                coinm_markets[symbol] = data

        if (
            account_type == AccountType.SPOT
            or account_type == AccountType.SPOT_TESTNET
            or account_type == AccountType.MARGIN
            or account_type == AccountType.ISOLATED_MARGIN
        ):
            return spot_markets
        elif (
            account_type == AccountType.USD_M_FUTURE
            or account_type == AccountType.USD_M_FUTURE_TESTNET
        ):
            return usdm_markets
        elif (
            account_type == AccountType.COIN_M_FUTURE
            or account_type == AccountType.COIN_M_FUTURE_TESTNET
        ):
            return coinm_markets
        elif account_type == AccountType.PORTFOLIO_MARGIN:
            return market

    def _load_market_id(self):
        market_id = {}
        if not self.market:
            raise ValueError(
                "Market data not loaded, please call `load_markets()` first"
            )
        for _, v in self.market.items():
            if v["subType"] == "linear":
                market_id[f"{v['id']}_swap"] = v
            elif v["type"] == "spot":
                market_id[f"{v['id']}_spot"] = v
            else:
                market_id[v["id"]] = v
        return market_id
