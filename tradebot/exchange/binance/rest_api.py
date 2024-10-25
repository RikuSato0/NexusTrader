import time
import hmac
import hashlib
import asyncio
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urljoin
from tradebot.entity import Order

from tradebot.base import RestApi
from tradebot.exchange.binance.constants import BASE_URLS, ENDPOINTS
from tradebot.exchange.binance.constants import BinanceAccountType, EndpointsType


class BinanceRestApi(RestApi):
    def __init__(
        self,
        account_type: BinanceAccountType,
        api_key: str = None,
        secret: str = None,
        **kwargs,
    ):
        self._api_key = api_key
        self._secret = secret
        self._account_type = account_type
        self._base_url = BASE_URLS[account_type]
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
        """
        SPOT: https://developers.binance.com/docs/binance-spot-api-docs/rest-api#new-order-trade /api/v3/order 
        MARGIN: https://developers.binance.com/docs/margin_trading/trade/Margin-Account-New-Order /sapi/v1/margin/order
        USDM: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api /fapi/v1/order
        COINM: https://developers.binance.com/docs/derivatives/coin-margined-futures/trade /dapi/v1/order
        PORTFOLIO > USDM: https://developers.binance.com/docs/derivatives/portfolio-margin/trade /papi/v1/um/order
                  > COINM: https://developers.binance.com/docs/derivatives/portfolio-margin/trade/New-CM-Order /papi/v1/cm/order
                  > MARGIN: https://developers.binance.com/docs/derivatives/portfolio-margin/trade/New-Margin-Order /papi/v1/margin/order
        """
        endpoint = self._generate_endpoint(EndpointsType.TRADING)
        endpoint = f"{endpoint}/order"
        params = {"symbol": symbol, "side": side, "type": type, **kwargs}
        return await self._fetch("POST", endpoint, data=params, signed=True)

    
    def _generate_endpoint(self, endpoint_type: EndpointsType) -> str:
        return ENDPOINTS[endpoint_type][self._account_type]

#     async def _new_order(
#         self,
#         symbol: str,
#         side: Literal["buy", "sell"],
#         order_type: Literal["LIMIT", "MARKET"],
#         amount: Decimal,
#         price: Optional[float] = None,
#         **params,
#     ) -> Order:
#         try:
#             endpoint = self._generate_endpoint(EndpointsType.TRADING)
#             endpoint = f"{endpoint}/order"
#             order_params = {
#                 "symbol": symbol,
#                 "side": side.upper(),
#                 "type": order_type,
#                 "quantity": str(amount),
#                 **params,
#             }
#             if order_type == "LIMIT":
#                 order_params["price"] = str(price)
#                 # order_params["timeInForce"] = params.get("timeInForce", "GTC")

#             res = await self._fetch("POST", endpoint, data=order_params, signed=True)
#             # return parse_binance_order(res, self.exchange_id)
#             return res
#         except Exception as e:
#             self._log.error(f"Failed to place {order_type.lower()} order: {str(e)}")
#             return Order(
#                 raw={},
#                 success=False,
#                 exchange=self.exchange_id,
#                 id=None,
#                 client_order_id=None,
#                 timestamp=time.time_ns() // 1_000_000,
#                 symbol=symbol,
#                 type=order_type.lower(),
#                 side=side,
#                 status="failed",
#                 price=price,
#                 amount=amount,
#             )

#     async def place_limit_order(
#         self,
#         symbol: str,
#         side: Literal["buy", "sell"],
#         amount: Decimal,
#         price: float,
#         **params,
#     ) -> Order:
#         return await self._new_order(symbol, side, "LIMIT", amount, price, **params)

#     async def place_market_order(
#         self, symbol: str, side: Literal["buy", "sell"], amount: Decimal, **params
#     ) -> Order:
#         return await self._new_order(symbol, side, "MARKET", amount, **params)

#     async def cancel_order(self, id: str, symbol: str, **params) -> Order:
#         try:
#             endpoint = self._generate_endpoint(EndpointsType.TRADING)
#             endpoint = f"{endpoint}/order"
#             cancel_params = {"symbol": symbol, "orderId": id, **params}
#             res = await self._fetch(
#                 "DELETE", endpoint, params=cancel_params, signed=True
#             )
#             # return parse_binance_order(res, self.exchange_id)
#             return res
#         except Exception as e:
#             self._log.error(f"Failed to cancel order: {str(e)}")
#             return Order(
#                 raw={},
#                 success=False,
#                 exchange=self.exchange_id,
#                 id=id,
#                 client_order_id=None,
#                 timestamp=time.time_ns() // 1_000_000,
#                 symbol=symbol,
#                 type=None,
#                 side=None,
#                 status="failed",
#                 amount=None,
#             )

#     async def fetch_orders(
#         self, symbol: str, since: int = None, limit: int = None
#     ) -> List[Order]:
#         endpoint = self._generate_endpoint(EndpointsType.TRADING)
#         endpoint = f"{endpoint}/allOrders"
#         params = {"symbol": symbol}
#         if since:
#             params["startTime"] = since
#         if limit:
#             params["limit"] = limit
#         res = await self._fetch("GET", endpoint, params=params, signed=True)
#         # return [parse_binance_order(order, self.exchange_id) for order in res]
#         return res

#     async def handle_request_timeout(self, method: str, params: Dict[str, Any]):
#         symbol = params["symbol"]
#         current_time = time.time_ns() // 1_000_000
#         orders = await self.fetch_orders(symbol, since=current_time - 1000 * 5)

#         if not self._in_orders(orders, method, params):
#             match method:
#                 case "place_limit_order":
#                     return await self.retry_place_limit_order(params)
#                 case "place_market_order":
#                     return await self.retry_place_market_order(params)
#                 case "cancel_order":
#                     return await self.retry_cancel_order(params)

#     async def retry_place_limit_order(
#         self, params: Dict[str, Any], max_retry: int = 3, interval: int = 3
#     ):
#         for i in range(max_retry):
#             res = await self.place_limit_order(**params)

#             if res.success:
#                 return res

#             if i == max_retry - 1:
#                 return Order(
#                     raw={},
#                     success=False,
#                     exchange=self.exchange_id,
#                     id=params.get("id", None),
#                     client_order_id="",
#                     timestamp=time.time_ns() // 1_000_000,
#                     symbol=params.get("symbol", None),
#                     type="limit",
#                     side=params["side"],
#                     price=params.get("price", None),
#                     amount=params.get("amount", None),
#                     status="failed",
#                 )

#             self._log.warn(
#                 f"Order placement failed, attempting retry {i+1} of {max_retry}: {str(res)}"
#             )
#             await asyncio.sleep(interval)

#     async def retry_place_market_order(
#         self, params: Dict[str, Any], max_retry: int = 3, interval: int = 3
#     ):
#         for i in range(max_retry):
#             res = await self.place_market_order(**params)

#             if res.success:
#                 return res

#             if i == max_retry - 1:
#                 return Order(
#                     raw={},
#                     success=False,
#                     exchange=self.exchange_id,
#                     id=params.get("id", None),
#                     client_order_id="",
#                     timestamp=time.time_ns() // 1_000_000,
#                     symbol=params.get("symbol", None),
#                     type="market",
#                     side=params.get("side", None),
#                     amount=params.get("amount", None),
#                     status="failed",
#                 )

#             self._log.warn(
#                 f"Order placement failed, attempting retry {i+1} of {max_retry}: {str(res)}"
#             )
#             await asyncio.sleep(interval)

#     async def retry_cancel_order(
#         self, params: Dict[str, Any], max_retry: int = 3, interval: int = 3
#     ):
#         for i in range(max_retry):
#             res = await self.cancel_order(**params)

#             if res.success:
#                 return res

#             if i == max_retry - 1:
#                 return Order(
#                     raw={},
#                     success=False,
#                     exchange=self.exchange_id,
#                     id=params.get("id", None),
#                     client_order_id="",
#                     timestamp=time.time_ns() // 1_000_000,
#                     symbol=params.get("symbol", None),
#                     type=None,
#                     side=None,
#                     status="failed",
#                     amount=None,
#                 )

#             self._log.warn(
#                 f"Order cancellation failed, attempting retry {i+1} of {max_retry}: {str(res)}"
#             )
#             await asyncio.sleep(interval)

#     def _in_orders(
#         self, orders: List[Order], method: str, params: Dict[str, Any]
#     ) -> bool:
#         # Implement logic to check if the order is in the list of orders
#         # This will depend on the specific details of your Order class and how you want to match orders
#         pass


# def parse_binance_order(binance_order: Dict[str, Any], exchange_id: str) -> Order:
#     status_map = {
#         "NEW": "new",
#         "PARTIALLY_FILLED": "partially_filled",
#         "FILLED": "filled",
#         "CANCELED": "canceled",
#         "EXPIRED": "expired",
#         "REJECTED": "failed",
#     }

#     order_type_map = {
#         "LIMIT": "limit",
#         "MARKET": "market",
#         "STOP_LOSS": "limit",
#         "STOP_LOSS_LIMIT": "limit",
#         "TAKE_PROFIT": "limit",
#         "TAKE_PROFIT_LIMIT": "limit",
#         "LIMIT_MAKER": "limit",
#     }

#     return Order(
#         raw=binance_order,
#         success=True,
#         exchange=exchange_id,
#         id=str(binance_order["orderId"]),
#         client_order_id=binance_order["clientOrderId"],
#         timestamp=int(binance_order["time"]),
#         symbol=binance_order["symbol"],
#         type=order_type_map.get(binance_order["type"], "limit"),
#         side=binance_order["side"].lower(),
#         status=status_map.get(binance_order["status"], "failed"),
#         price=float(binance_order["price"]) if binance_order["price"] != "0" else None,
#         average=float(binance_order["price"])
#         if binance_order["status"] == "FILLED"
#         else None,
#         last_filled_price=None,  # Binance doesn't provide this directly
#         amount=Decimal(binance_order["origQty"]),
#         filled=Decimal(binance_order["executedQty"]),
#         last_filled=None,  # Binance doesn't provide this directly
#         remaining=Decimal(binance_order["origQty"])
#         - Decimal(binance_order["executedQty"]),
#         fee=None,  # Binance doesn't provide this in the order response
#         fee_currency=None,  # Binance doesn't provide this in the order response
#         cost=float(binance_order["cummulativeQuoteQty"])
#         if binance_order["cummulativeQuoteQty"] != "0"
#         else None,
#         last_trade_timestamp=int(binance_order["updateTime"]),
#         reduce_only=None,  # This is not applicable for spot orders
#         position_side=None,  # This is not applicable for spot orders
#         time_in_force=binance_order.get("timeInForce"),
#         leverage=None,  # This is not applicable for spot orders
#     )
