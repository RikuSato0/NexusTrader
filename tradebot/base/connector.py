from abc import ABC, abstractmethod
from typing import Dict
from decimal import Decimal


from aiolimiter import AsyncLimiter

from tradebot.base.ws_client import WSClient
from tradebot.base.api_client import ApiClient
from tradebot.schema import Order, BaseMarket
from tradebot.constants import ExchangeType
from tradebot.core.log import SpdLog
from tradebot.core.entity import RateLimit
from tradebot.constants import OrderSide, OrderType, TimeInForce, PositionSide
from tradebot.core.nautilius_core import LiveClock, MessageBus
from tradebot.schema import AccountBalance



class PublicConnector(ABC):
    def __init__(
        self,
        account_type,
        market: Dict[str, BaseMarket],
        market_id: Dict[str, str],
        exchange_id: ExchangeType,
        ws_client: WSClient,
        msgbus: MessageBus,
    ):
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )
        self._account_type = account_type
        self._market = market
        self._market_id = market_id
        self._exchange_id = exchange_id
        self._ws_client = ws_client
        self._msgbus = msgbus
        self._clock = LiveClock()

    @property
    def account_type(self):
        return self._account_type

    @abstractmethod
    async def subscribe_trade(self, symbol: str):
        pass

    @abstractmethod
    async def subscribe_bookl1(self, symbol: str):
        pass

    @abstractmethod
    async def subscribe_kline(self, symbol: str, interval: str):
        pass

    async def disconnect(self):
        self._ws_client.disconnect()  # not needed to await


class PrivateConnector(ABC):
    def __init__(
        self,
        account_type,
        market: Dict[str, BaseMarket],
        market_id: Dict[str, str],
        exchange_id: ExchangeType,
        ws_client: WSClient,
        api_client: ApiClient,
        msgbus: MessageBus,
        rate_limit: RateLimit | None = None,
    ):
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )
        self._account_type = account_type
        self._market = market
        self._market_id = market_id
        self._exchange_id = exchange_id
        self._ws_client = ws_client
        self._api_client = api_client
        self._clock = LiveClock()
        self._msgbus: MessageBus = msgbus
        self._account_balance: AccountBalance = AccountBalance()

        if rate_limit:
            self._limiter = AsyncLimiter(rate_limit.max_rate, rate_limit.time_period)
        else:
            self._limiter = None

    @property
    def account_type(self):
        return self._account_type

    @abstractmethod
    async def _init_account_balance(self):
        pass

    @abstractmethod
    async def create_order(
        self,
        symbol: str,
        side: OrderSide,
        type: OrderType,
        amount: Decimal,
        price: Decimal,
        time_in_force: TimeInForce,
        position_side: PositionSide,
        **kwargs,
    ) -> Order:
        pass

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str, **kwargs) -> Order:
        pass

    @abstractmethod
    async def connect(self):
        await self._init_account_balance()

    async def disconnect(self):
        self._ws_client.disconnect()
        await self._api_client.close_session()
