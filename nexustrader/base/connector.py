from abc import ABC, abstractmethod
from typing import Dict
from decimal import Decimal


from aiolimiter import AsyncLimiter

from nexustrader.base.ws_client import WSClient
from nexustrader.base.api_client import ApiClient
from nexustrader.schema import Order, BaseMarket, Kline
from nexustrader.constants import ExchangeType
from nexustrader.core.log import SpdLog
from nexustrader.core.cache import AsyncCache
from nexustrader.core.entity import RateLimit, TaskManager
from nexustrader.constants import (
    OrderSide,
    OrderType,
    TimeInForce,
    PositionSide,
    KlineInterval,
    TriggerType,
)
from nexustrader.core.nautilius_core import LiveClock, MessageBus


class PublicConnector(ABC):
    def __init__(
        self,
        account_type,
        market: Dict[str, BaseMarket],
        market_id: Dict[str, str],
        exchange_id: ExchangeType,
        ws_client: WSClient,
        msgbus: MessageBus,
        api_client: ApiClient,
        task_manager: TaskManager,
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
        self._msgbus = msgbus
        self._api_client = api_client
        self._clock = LiveClock()
        self._task_manager = task_manager
        
        if rate_limit:
            self._limiter = AsyncLimiter(rate_limit.max_rate, rate_limit.time_period)
        else:
            self._limiter = None
        
    @property
    def account_type(self):
        return self._account_type

    @abstractmethod
    def request_klines(
        self,
        symbol: str,
        interval: KlineInterval,
        limit: int | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[Kline]:
        """Request klines"""
        pass

    @abstractmethod
    async def subscribe_trade(self, symbol: str):
        """Subscribe to the trade data"""
        pass

    @abstractmethod
    async def subscribe_bookl1(self, symbol: str):
        """Subscribe to the bookl1 data"""
        pass

    @abstractmethod
    async def subscribe_kline(self, symbol: str, interval: KlineInterval):
        """Subscribe to the kline data"""
        pass

    async def disconnect(self):
        """Disconnect from the exchange"""
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
        cache: AsyncCache,
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
        self._cache = cache
        self._clock = LiveClock()
        self._msgbus: MessageBus = msgbus

        if rate_limit:
            self._limiter = AsyncLimiter(rate_limit.max_rate, rate_limit.time_period)
        else:
            self._limiter = None

    @property
    def account_type(self):
        return self._account_type

    @abstractmethod
    async def _init_account_balance(self):
        """Initialize the account balance"""
        pass

    @abstractmethod
    async def _init_position(self):
        """Initialize the position"""
        pass

    @abstractmethod
    async def create_stop_loss_order(
        self,
        symbol: str,
        side: OrderSide,
        type: OrderType,
        amount: Decimal,
        trigger_price: Decimal,
        trigger_type: TriggerType = TriggerType.LAST_PRICE,
        price: Decimal | None = None,
        time_in_force: TimeInForce = TimeInForce.GTC,
        position_side: PositionSide | None = None,
        **kwargs,
    ) -> Order:
        """Create a stop loss order"""
        pass

    @abstractmethod
    async def create_take_profit_order(
        self,
        symbol: str,
        side: OrderSide,
        type: OrderType,
        amount: Decimal,
        trigger_price: Decimal,
        trigger_type: TriggerType = TriggerType.LAST_PRICE,
        price: Decimal | None = None,
        time_in_force: TimeInForce = TimeInForce.GTC,
        position_side: PositionSide | None = None,
        **kwargs,
    ) -> Order:
        """Create a take profit order"""
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
        """Create an order"""
        pass

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str, **kwargs) -> Order:
        """Cancel an order"""
        pass

    @abstractmethod
    async def connect(self):
        """Connect to the exchange"""
        await self._init_account_balance()
        await self._init_position()

    async def disconnect(self):
        """Disconnect from the exchange"""
        self._ws_client.disconnect()
        await self._api_client.close_session()
