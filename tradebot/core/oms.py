import asyncio
from typing import Dict
from tradebot.constants import AccountType
from tradebot.base import PrivateConnector
from tradebot.schema import Order, OrderSubmit, InstrumentId, ExchangeType
from tradebot.constants import OrderStatus
from tradebot.core.cache import AsyncCache
from tradebot.core.log import SpdLog
from tradebot.core.nautilius_core import MessageBus
from tradebot.core.entity import TaskManager
from tradebot.exchange.binance import BinanceAccountType
from tradebot.exchange.bybit import BybitAccountType


class OrderManagerSystem:
    BINANCE_SPOT_PRIORITY = [
        BinanceAccountType.ISOLATED_MARGIN,
        BinanceAccountType.MARGIN,
        BinanceAccountType.SPOT_TESTNET,
        BinanceAccountType.SPOT,
    ]

    def __init__(
        self,
        cache: AsyncCache,
        msgbus: MessageBus,
        task_manager: TaskManager,
        private_connectors: Dict[AccountType, PrivateConnector],
    ):
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )
        self._cache = cache
        self._msgbus = msgbus
        self._task_manager = task_manager
        self._private_connectors = private_connectors
        
        self._uuid_to_order_id = {}
        self._order_id_to_uuid = {}

        # Order and position message queues
        self._order_msg_queue: asyncio.Queue[Order] = asyncio.Queue()
        self._position_msg_queue: asyncio.Queue[Order] = asyncio.Queue()

        # Order execution queues
        self._order_submit_queues: Dict[AccountType, asyncio.Queue[OrderSubmit]] = {}
        self._cancel_order_queues: Dict[AccountType, asyncio.Queue[OrderSubmit]] = {}

        # Binance account types
        self._binance_spot_account_type: BinanceAccountType = None
        self._binance_linear_account_type: BinanceAccountType = None
        self._binance_inverse_account_type: BinanceAccountType = None
        self._binance_pm_account_type: BinanceAccountType = None
        self._bybit_account_type: BybitAccountType = None

        # Set up message bus subscriptions
        self._msgbus.subscribe(topic="order", handler=self._add_order_msg)
        self._msgbus.subscribe(topic="order", handler=self._add_position_msg)

        # Initialize account types
        self._set_binance_account_type()
        self._set_bybit_account_type()
        # TODO: set okx account type
        self._build_order_submit_queues()

    def _build_order_submit_queues(self):
        for account_type in self._private_connectors:
            self._order_submit_queues[account_type] = asyncio.Queue()
            self._cancel_order_queues[account_type] = asyncio.Queue()

    def _set_bybit_account_type(self):
        account_types = self._private_connectors.keys()
        self._bybit_account_type = (
            BybitAccountType.ALL_TESTNET
            if BybitAccountType.ALL_TESTNET in account_types
            else BybitAccountType.ALL
        )

    def _set_binance_account_type(self):
        account_types = self._private_connectors.keys()

        if BinanceAccountType.PORTFOLIO_MARGIN in account_types:
            self._binance_pm_account_type = BinanceAccountType.PORTFOLIO_MARGIN
            return

        for account_type in self.BINANCE_SPOT_PRIORITY:
            if account_type in account_types:
                self._binance_spot_account_type = account_type
                break

        self._binance_linear_account_type = (
            BinanceAccountType.USD_M_FUTURE_TESTNET
            if BinanceAccountType.USD_M_FUTURE_TESTNET in account_types
            else BinanceAccountType.USD_M_FUTURE
        )

        self._binance_inverse_account_type = (
            BinanceAccountType.COIN_M_FUTURE_TESTNET
            if BinanceAccountType.COIN_M_FUTURE_TESTNET in account_types
            else BinanceAccountType.COIN_M_FUTURE
        )

    def _instrument_id_to_account_type(
        self, instrument_id: InstrumentId
    ) -> AccountType:
        match instrument_id.exchange:
            case ExchangeType.BINANCE:
                if self._binance_pm_account_type:
                    return self._binance_pm_account_type
                if instrument_id.is_spot:
                    return self._binance_spot_account_type
                elif instrument_id.is_linear:
                    return self._binance_linear_account_type
                elif instrument_id.is_inverse:
                    return self._binance_inverse_account_type
            case ExchangeType.BYBIT:
                return self._bybit_account_type
            case ExchangeType.OKX:
                pass

    def _submit_order(self, order: OrderSubmit, account_type: AccountType | None = None):
        instrument_id = InstrumentId.from_str(order.symbol)
        if not account_type:
            account_type = self._instrument_id_to_account_type(instrument_id)
        self._order_submit_queues[account_type].put_nowait(order)

    def _submit_cancel_order(
        self, order: OrderSubmit, account_type: AccountType | None = None
    ):
        instrument_id = InstrumentId.from_str(order.symbol)
        if not account_type:
            account_type = self._instrument_id_to_account_type(instrument_id)
        self._cancel_order_queues[account_type].put_nowait(order)

    def _add_order_msg(self, order: Order):
        self._order_msg_queue.put_nowait(order)

    def _add_position_msg(self, order: Order):
        self._position_msg_queue.put_nowait(order)

    async def _handle_cancel_order(
        self, account_type: AccountType, queue: asyncio.Queue[OrderSubmit]
    ):
        while True:
            order_submit = await queue.get()
            
            order_id = self._uuid_to_order_id.get(order_submit.uuid, None)
            if order_id:
                order: Order = await self._private_connectors[account_type].cancel_order(
                    symbol=order_submit.symbol,
                    order_id=order_id,
                    **order_submit.kwargs,
                )
                order.uuid = order_submit.uuid
                self._msgbus.publish(topic="order", msg=order) # INITIALIZED -> CANCELING
            else:
                self._log.error(f"Order ID not found for UUID: {order_submit.uuid}, The order may already be canceled or filled or not exist")            
            queue.task_done()

    async def _handle_submit_order(
        self, account_type: AccountType, queue: asyncio.Queue[OrderSubmit]
    ):
        while True:
            order_submit = await queue.get()
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
                self._order_id_to_uuid[order.id] = order.uuid
                self._uuid_to_order_id[order.uuid] = order.id
            self._msgbus.publish(topic="order", msg=order) # INITIALIZED -> PENDING
            queue.task_done()
            

    async def _handle_position_event(self):
        while True:
            try:
                order = await self._position_msg_queue.get()
                self._cache._apply_position(order)
                self._position_msg_queue.task_done()
            except Exception as e:
                self._log.error(f"Error in handle_position_event: {e}")

    async def _handle_order_event(self):
        while True:
            try:
                order = await self._order_msg_queue.get()
                match order.status:
                    case OrderStatus.PENDING:
                        self._log.debug(f"ORDER STATUS PENDING: {str(order)}")
                        self._cache._order_initialized(order)
                        self._msgbus.send(endpoint="pending", msg=order)
                    case OrderStatus.CANCELING:
                        self._log.debug(f"ORDER STATUS CANCELING: {str(order)}")
                        self._cache._order_status_update(order)
                        self._msgbus.send(endpoint="canceling", msg=order)
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
                    case OrderStatus.FILLED:
                        self._log.debug(f"ORDER STATUS FILLED: {str(order)}")
                        self._cache._order_status_update(order)
                        self._msgbus.send(endpoint="filled", msg=order)
                    case OrderStatus.EXPIRED:
                        self._log.debug(f"ORDER STATUS EXPIRED: {str(order)}")
                        self._cache._order_status_update(order)
                    case OrderStatus.FAILED:
                        self._log.debug(f"ORDER STATUS FAILED: {str(order)}")
                        self._cache._order_status_update(order)
                        self._msgbus.send(endpoint="failed", msg=order)
                self._order_msg_queue.task_done()
            except Exception as e:
                self._log.error(f"Error in handle_order_event: {e}")

    async def start(self):
        self._log.debug("OrderManagerSystem started")

        # Start order execution handlers
        for account_type in self._private_connectors.keys():
            self._task_manager.create_task(
                self._handle_submit_order(
                    account_type, self._order_submit_queues[account_type]
                )
            )
            self._task_manager.create_task(
                self._handle_cancel_order(
                    account_type, self._cancel_order_queues[account_type]
                )
            )

        # Start order and position event handlers
        self._task_manager.create_task(self._handle_order_event())
        self._task_manager.create_task(self._handle_position_event())
