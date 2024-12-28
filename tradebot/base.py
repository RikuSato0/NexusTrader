import asyncio
import ssl
import certifi
import orjson
import warnings
import aiohttp


import ccxt
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from typing import Callable, Literal
from decimal import Decimal


from aiolimiter import AsyncLimiter
from decimal import ROUND_HALF_UP, ROUND_CEILING, ROUND_FLOOR

from tradebot.schema import Order, BaseMarket
from tradebot.constants import ExchangeType
from tradebot.core.log import SpdLog
from tradebot.core.entity import TaskManager, RateLimit
from tradebot.constants import OrderSide, OrderType, TimeInForce, PositionSide
from picows import (
    ws_connect,
    WSFrame,
    WSTransport,
    WSListener,
    WSMsgType,
    WSAutoPingStrategy,
)
from tradebot.core.nautilius_core import LiveClock, MessageBus
from tradebot.core.cache import AsyncCache
from tradebot.core.registry import OrderRegistry
from tradebot.constants import AccountType, SubmitType, OrderStatus
from tradebot.schema import OrderSubmit, AccountBalance, FuturePosition


class ExchangeManager(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("apiKey", None)
        self.secret = config.get("secret", None)
        self.exchange_id = ExchangeType(config["exchange_id"])
        self.api = self._init_exchange()
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="INFO", flush=True
        )
        self.is_testnet = config.get("sandbox", False)
        self.market: Dict[str, BaseMarket] = {}
        self.market_id: Dict[str, str] = {}

        if not self.api_key or not self.secret:
            warnings.warn(
                "API Key and Secret not provided, So some features related to trading will not work"
            )
        self.load_markets()

    def _init_exchange(self) -> ccxt.Exchange:
        try:
            exchange_class = getattr(ccxt, self.config["exchange_id"])
        except AttributeError:
            raise AttributeError(
                f"Exchange {self.config['exchange_id']} is not supported"
            )

        api = exchange_class(self.config)
        api.set_sandbox_mode(
            self.config.get("sandbox", False)
        )  # Set sandbox mode if demo trade is enabled
        return api

    def _parse_symbol(self, mkt: BaseMarket, exchange_suffix: str) -> str:
        if mkt.spot:
            return f"{mkt.base}{mkt.quote}.{exchange_suffix}"
        elif mkt.future:
            symbol = mkt.symbol
            expiry_suffix = symbol.split("-")[-1]
            return f"{mkt.base}{mkt.quote}-{expiry_suffix}.{exchange_suffix}"
        elif mkt.linear:
            return f"{mkt.base}{mkt.quote}-PERP.{exchange_suffix}"
        elif mkt.inverse:
            return f"{mkt.base}{mkt.quote}-PERP.{exchange_suffix}"

    @abstractmethod
    def load_markets(self):
        pass

    @property
    def linear(self):
        symbols = []
        for symbol, market in self.market.items():
            if market.linear and market.active and not market.future:
                symbols.append(symbol)
        return symbols

    @property
    def inverse(self):
        symbols = []
        for symbol, market in self.market.items():
            if market.inverse and market.active and not market.future:
                symbols.append(symbol)
        return symbols

    @property
    def spot(self):
        symbols = []
        for symbol, market in self.market.items():
            if market.spot and market.active:
                symbols.append(symbol)
        return symbols

    @property
    def future(self):
        symbols = []
        for symbol, market in self.market.items():
            if market.future and market.active:
                symbols.append(symbol)
        return symbols


class Listener(WSListener):
    def __init__(self, logger, specific_ping_msg=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._log = logger
        self.msg_queue = asyncio.Queue()
        self._specific_ping_msg = specific_ping_msg

    def send_user_specific_ping(self, transport: WSTransport):
        if self._specific_ping_msg:
            transport.send(WSMsgType.TEXT, self._specific_ping_msg)
            self._log.debug(f"Sent user specific ping {self._specific_ping_msg}")
        else:
            transport.send_ping()
            self._log.debug("Sent default ping.")

    def on_ws_connected(self, transport: WSTransport):
        self._log.debug("Connected to Websocket...")

    def on_ws_disconnected(self, transport: WSTransport):
        self._log.debug("Disconnected from Websocket.")

    def on_ws_frame(self, transport: WSTransport, frame: WSFrame):
        try:
            match frame.msg_type:
                case WSMsgType.PING:
                    # Only send pong if auto_pong is disabled
                    transport.send_pong(frame.get_payload_as_bytes())
                    return
                case WSMsgType.TEXT:
                    # Queue raw bytes for handler to decode
                    self.msg_queue.put_nowait(frame.get_payload_as_bytes())
                    return
                case WSMsgType.CLOSE:
                    close_code = frame.get_close_code()
                    close_msg = frame.get_close_message()
                    self._log.warning(
                        f"Received close frame. Close code: {close_code}, Close message: {close_msg}"
                    )
                    return
        except Exception as e:
            self._log.error(f"Error processing message: {str(e)}")


class WSClient(ABC):
    def __init__(
        self,
        url: str,
        limiter: AsyncLimiter,
        handler: Callable[..., Any],
        task_manager: TaskManager,
        specific_ping_msg: bytes = None,
        reconnect_interval: int = 1,
        ping_idle_timeout: int = 2,
        ping_reply_timeout: int = 1,
        auto_ping_strategy: Literal[
            "ping_when_idle", "ping_periodically"
        ] = "ping_when_idle",
        enable_auto_ping: bool = True,
        enable_auto_pong: bool = False,
    ):
        self._clock = LiveClock()
        self._url = url
        self._specific_ping_msg = specific_ping_msg
        self._reconnect_interval = reconnect_interval
        self._ping_idle_timeout = ping_idle_timeout
        self._ping_reply_timeout = ping_reply_timeout
        self._enable_auto_pong = enable_auto_pong
        self._enable_auto_ping = enable_auto_ping
        self._listener: Listener = None
        self._transport = None
        self._subscriptions = {}
        self._limiter = limiter
        self._callback = handler
        if auto_ping_strategy == "ping_when_idle":
            self._auto_ping_strategy = WSAutoPingStrategy.PING_WHEN_IDLE
        elif auto_ping_strategy == "ping_periodically":
            self._auto_ping_strategy = WSAutoPingStrategy.PING_PERIODICALLY
        self._task_manager = task_manager
        self._log = SpdLog.get_logger(type(self).__name__, level="DEBUG", flush=True)

    @property
    def connected(self):
        return self._transport and self._listener

    async def _connect(self):
        WSListenerFactory = lambda: Listener(self._log, self._specific_ping_msg)  # noqa: E731
        self._transport, self._listener = await ws_connect(
            WSListenerFactory,
            self._url,
            enable_auto_ping=self._enable_auto_ping,
            auto_ping_idle_timeout=self._ping_idle_timeout,
            auto_ping_reply_timeout=self._ping_reply_timeout,
            auto_ping_strategy=self._auto_ping_strategy,
            enable_auto_pong=self._enable_auto_pong,
        )

    async def connect(self):
        if not self.connected:
            await self._connect()
            self._task_manager.create_task(self._msg_handler(self._listener.msg_queue))
            self._task_manager.create_task(self._connection_handler())

    async def _connection_handler(self):
        while True:
            try:
                if not self.connected:
                    await self._connect()
                    self._task_manager.create_task(
                        self._msg_handler(self._listener.msg_queue)
                    )
                    await self._resubscribe()
                await self._transport.wait_disconnected()
            except Exception as e:
                self._log.error(f"Connection error: {e}")
            finally:
                self._log.debug("Websocket reconnecting...")
                self._transport, self._listener = None, None
                await asyncio.sleep(self._reconnect_interval)

    async def _send(self, payload: dict):
        await self._limiter.acquire()
        self._transport.send(WSMsgType.TEXT, orjson.dumps(payload))

    async def _msg_handler(self, queue: asyncio.Queue):
        while True:
            msg = await queue.get()
            self._callback(msg)
            queue.task_done()

    def disconnect(self):
        if self.connected:
            self._transport.disconnect()

    @abstractmethod
    async def _resubscribe(self):
        pass


class ApiClient(ABC):
    def __init__(
        self,
        api_key: str = None,
        secret: str = None,
        timeout: int = 10,
    ):
        self._api_key = api_key
        self._secret = secret
        self._timeout = timeout
        self._log = SpdLog.get_logger(type(self).__name__, level="DEBUG", flush=True)
        self._ssl_context = ssl.create_default_context(cafile=certifi.where())
        self._session: Optional[aiohttp.ClientSession] = None
        self._clock = LiveClock()

    async def _init_session(self):
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            tcp_connector = aiohttp.TCPConnector(
                ssl=self._ssl_context, enable_cleanup_closed=True
            )
            self._session = aiohttp.ClientSession(
                connector=tcp_connector, json_serialize=orjson.dumps, timeout=timeout
            )

    async def close_session(self):
        if self._session:
            await self._session.close()
            self._session = None

    @abstractmethod
    def raise_error(self, raw: bytes, status: int, headers: Dict[str, Any]):
        raise NotImplementedError("Subclasses must implement this method.")


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


class ExecutionManagementSystem(ABC):
    def __init__(
        self,
        market: Dict[str, BaseMarket],
        cache: AsyncCache,
        msgbus: MessageBus,
        task_manager: TaskManager,
        registry: OrderRegistry,
    ):
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )

        self._market = market
        self._cache = cache
        self._msgbus = msgbus
        self._task_manager = task_manager
        self._registry = registry

        self._order_submit_queues: Dict[AccountType, asyncio.Queue[OrderSubmit]] = {}
        self._private_connectors: Dict[AccountType, PrivateConnector] | None = None

    def _build(self, private_connectors: Dict[AccountType, PrivateConnector]):
        self._private_connectors = private_connectors
        self._build_order_submit_queues()
        self._set_account_type()

    def _amount_to_precision(
        self,
        symbol: str,
        amount: float,
        mode: Literal["round", "ceil", "floor"] = "round",
    ) -> Decimal:
        market = self._market[symbol]
        amount: Decimal = Decimal(str(amount))
        precision = market.precision.amount

        if precision >= 1:
            exp = Decimal(int(precision))
            precision_decimal = Decimal("1")
        else:
            exp = Decimal("1")
            precision_decimal = Decimal(str(precision))

        if mode == "round":
            amount = (amount / exp).quantize(
                precision_decimal, rounding=ROUND_HALF_UP
            ) * exp
        elif mode == "ceil":
            amount = (amount / exp).quantize(
                precision_decimal, rounding=ROUND_CEILING
            ) * exp
        elif mode == "floor":
            amount = (amount / exp).quantize(
                precision_decimal, rounding=ROUND_FLOOR
            ) * exp

        return amount

    def _price_to_precision(
        self,
        symbol: str,
        price: float,
        mode: Literal["round", "ceil", "floor"] = "round",
    ) -> Decimal:
        market = self._market[symbol]
        price: Decimal = Decimal(str(price))

        decimal = market.precision.price

        if decimal >= 1:
            exp = Decimal(int(decimal))
            precision_decimal = Decimal("1")
        else:
            exp = Decimal("1")
            precision_decimal = Decimal(str(decimal))

        if mode == "round":
            price = (price / exp).quantize(
                precision_decimal, rounding=ROUND_HALF_UP
            ) * exp
        elif mode == "ceil":
            price = (price / exp).quantize(
                precision_decimal, rounding=ROUND_CEILING
            ) * exp
        elif mode == "floor":
            price = (price / exp).quantize(
                precision_decimal, rounding=ROUND_FLOOR
            ) * exp

        return price

    @abstractmethod
    def _build_order_submit_queues(self):
        pass

    @abstractmethod
    def _set_account_type(self):
        pass

    @abstractmethod
    def _submit_order(
        self, order: OrderSubmit, account_type: AccountType | None = None
    ):
        pass

    async def _cancel_order(self, order_submit: OrderSubmit, account_type: AccountType):
        order_id = self._registry.get_order_id(order_submit.uuid)
        if order_id:
            order: Order = await self._private_connectors[account_type].cancel_order(
                symbol=order_submit.symbol,
                order_id=order_id,
                **order_submit.kwargs,
            )
            order.uuid = order_submit.uuid
            if order.success:
                self._cache._order_status_update(order)  # SOME STATUS -> CANCELING
                self._msgbus.send(endpoint="canceling", msg=order)
            else:
                # self._cache._order_status_update(order) # SOME STATUS -> FAILED
                self._msgbus.send(endpoint="cancel_failed", msg=order)
            return order
        else:
            self._log.error(
                f"Order ID not found for UUID: {order_submit.uuid}, The order may already be canceled or filled or not exist"
            )

    async def _create_order(self, order_submit: OrderSubmit, account_type: AccountType):
        order: Order = await self._private_connectors[account_type].create_order(
            symbol=order_submit.symbol,
            side=order_submit.side,
            type=order_submit.type,
            amount=order_submit.amount,
            price=order_submit.price,
            time_in_force=order_submit.time_in_force,
            position_side=order_submit.position_side,
            **order_submit.kwargs,
        )
        order.uuid = order_submit.uuid
        if order.success:
            self._registry.register_order(order)
            self._cache._order_initialized(order)  # INITIALIZED -> PENDING
            self._msgbus.send(endpoint="pending", msg=order)
        else:
            self._cache._order_status_update(order)  # INITIALIZED -> FAILED
            self._msgbus.send(endpoint="failed", msg=order)
        return order
    
    @abstractmethod
    def _get_min_order_amount(self, symbol: str, market: BaseMarket) -> Decimal:
        pass
    
    def _calculate_twap_orders(self, order_submit: OrderSubmit, market: BaseMarket) -> Tuple[List[Decimal], Decimal, float]:
        """
        Calculate the amount list and wait time for the twap order

        eg:
        amount_list = [10, 10, 10]
        wait = 10
        """
        amount_list = []
        symbol = order_submit.symbol
        total_amount: Decimal = order_submit.amount
        wait = order_submit.wait
        duration = order_submit.duration
        
        min_order_amount: Decimal = self._get_min_order_amount(symbol, market)       
        
        interval = duration // wait
        if total_amount < min_order_amount:
            warnings.warn(f"Amount {total_amount} is less than min order amount {min_order_amount}. No need to split orders.")
            wait = 0
            return [min_order_amount], wait
        
        base_amount = float(total_amount) / interval
        
        base_amount = max(min_order_amount, self._amount_to_precision(symbol, base_amount))
        
        interval = int(total_amount // base_amount)
        remaining = total_amount - interval * base_amount
        
        if remaining < min_order_amount:
            amount_list = [base_amount] * interval 
            amount_list[-1] += remaining
        else:
            amount_list = [base_amount] * interval + [remaining]
        
        wait = duration / len(amount_list)
        return amount_list, min_order_amount, wait
    
    async def _twap_order(self, order_submit: OrderSubmit, account_type: AccountType):
        amount_list, min_order_amount, wait = self._calculate_twap_orders(order_submit)
        for amount in amount_list:
            order_submit = OrderSubmit(
                symbol=order_submit.symbol,
                instrument_id=order_submit.instrument_id,
                submit_type=SubmitType.CREATE,
                type=OrderType.LIMIT,
                side=order_submit.side,
                amount=amount,
                position_side=order_submit.position_side,
                kwargs=order_submit.kwargs,
            )
            self._submit_order(order_submit, account_type)
            await asyncio.sleep(wait)

    async def _create_twap_order(
        self, order_submit: OrderSubmit, account_type: AccountType
    ):
        self._task_manager.create_task(self._twap_order(order_submit, account_type))

    async def _handle_submit_order(
        self, account_type: AccountType, queue: asyncio.Queue[OrderSubmit]
    ):
        self._log.debug(f"Handling orders for account type: {account_type}")
        while True:
            order_submit = await queue.get()
            self._log.debug(f"[ORDER SUBMIT]: {order_submit}")
            if order_submit.submit_type == SubmitType.CANCEL:
                await self._cancel_order(order_submit, account_type)
            elif order_submit.submit_type == SubmitType.CREATE:
                await self._create_order(order_submit, account_type)
            elif order_submit.submit_type == SubmitType.TWAP:
                await self._create_twap_order(order_submit, account_type)
            queue.task_done()

    async def start(self):
        for account_type in self._order_submit_queues.keys():
            self._task_manager.create_task(
                self._handle_submit_order(
                    account_type, self._order_submit_queues[account_type]
                )
            )


class OrderManagementSystem(ABC):
    def __init__(
        self,
        cache: AsyncCache,
        msgbus: MessageBus,
        task_manager: TaskManager,
        registry: OrderRegistry,
    ):
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )
        self._cache = cache
        self._msgbus = msgbus
        self._task_manager = task_manager
        self._registry = registry

        self._order_msg_queue: asyncio.Queue[Order] = asyncio.Queue()

    def _add_order_msg(self, order: Order):
        self._order_msg_queue.put_nowait(order)

    def _handle_spot_position_event(self, order: Order):
        self._cache._apply_spot_position(order)

    def _handle_future_position_event(self, position: FuturePosition):
        self._cache._apply_future_position(position)

    async def _handle_order_event(self):
        while True:
            try:
                order = await self._order_msg_queue.get()

                # handle the ACCEPTED, PARTIALLY_FILLED, CANCELED, FILLED, EXPIRED arived early than the order submit uuid
                uuid = self._registry.get_uuid(order.id)
                if not uuid:
                    await self._registry.wait_for_order_id(order.id)
                    uuid = self._registry.get_uuid(order.id)
                order.uuid = uuid

                match order.status:
                    case OrderStatus.ACCEPTED:
                        self._log.debug(f"ORDER STATUS ACCEPTED: {str(order)}")
                        self._cache._order_status_update(order)
                        self._msgbus.send(endpoint="accepted", msg=order)
                    case OrderStatus.PARTIALLY_FILLED:
                        self._log.debug(f"ORDER STATUS PARTIALLY FILLED: {str(order)}")
                        self._cache._order_status_update(order)
                        self._msgbus.send(endpoint="partially_filled", msg=order)
                    case OrderStatus.CANCELED:
                        self._log.debug(f"ORDER STATUS CANCELED: {str(order)}")
                        self._cache._order_status_update(order)
                        self._msgbus.send(endpoint="canceled", msg=order)
                        self._registry.remove_order(order)
                    case OrderStatus.FILLED:
                        self._log.debug(f"ORDER STATUS FILLED: {str(order)}")
                        self._cache._order_status_update(order)
                        self._msgbus.send(endpoint="filled", msg=order)
                        self._registry.remove_order(order)
                    case OrderStatus.EXPIRED:
                        self._log.debug(f"ORDER STATUS EXPIRED: {str(order)}")
                        self._cache._order_status_update(order)
                self._order_msg_queue.task_done()
            except Exception as e:
                self._log.error(f"Error in handle_order_event: {e}")

    async def start(self):
        self._log.debug("OrderManagementSystem started")

        # Start order and position event handlers
        self._task_manager.create_task(self._handle_order_event())
