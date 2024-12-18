import asyncio
from typing import Dict
from tradebot.constants import AccountType, ExchangeType
from tradebot.schema import OrderSubmit, InstrumentId, Order
from tradebot.base import PrivateConnector
from tradebot.core.cache import AsyncCache
from tradebot.core.nautilius_core import MessageBus
from tradebot.core.entity import TaskManager
from tradebot.core.log import SpdLog
from tradebot.core.registry import OrderRegistry
from tradebot.exchange.binance import BinanceAccountType
from tradebot.exchange.bybit import BybitAccountType
from tradebot.constants import SubmitType

class ExecutionManagementSystem:
    BINANCE_SPOT_PRIORITY = [
        BinanceAccountType.ISOLATED_MARGIN,
        BinanceAccountType.MARGIN,
        BinanceAccountType.SPOT_TESTNET,
        BinanceAccountType.SPOT,
    ]

    def __init__(
        self, cache: AsyncCache, msgbus: MessageBus, task_manager: TaskManager, registry: OrderRegistry
    ):
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )

        self._cache = cache
        self._msgbus = msgbus
        self._task_manager = task_manager
        self._registry = registry

        self._order_submit_queues: Dict[AccountType, asyncio.Queue[OrderSubmit]] = {}

        # Binance account types
        self._binance_spot_account_type: BinanceAccountType = None
        self._binance_linear_account_type: BinanceAccountType = None
        self._binance_inverse_account_type: BinanceAccountType = None
        self._binance_pm_account_type: BinanceAccountType = None
        self._bybit_account_type: BybitAccountType = None

        self._private_connectors: Dict[AccountType, PrivateConnector] | None = None

    def _build(self, private_connectors: Dict[AccountType, PrivateConnector]):
        self._private_connectors = private_connectors
        self._build_order_submit_queues()
        self._set_bybit_account_type()
        self._set_binance_account_type()
        # TODO: set okx account type

    def _build_order_submit_queues(self):
        for account_type in self._private_connectors.keys():
            self._order_submit_queues[account_type] = asyncio.Queue()

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

    def _submit_order(
        self, order: OrderSubmit, account_type: AccountType | None = None
    ):
        instrument_id = InstrumentId.from_str(order.symbol)
        if not account_type:
            account_type = self._instrument_id_to_account_type(instrument_id)
        self._order_submit_queues[account_type].put_nowait(order)

    async def _handle_cancel_order(
        self, order_submit: OrderSubmit, account_type: AccountType
    ):
        order_id = self._registry.get_order_id(order_submit.uuid)
        if order_id:
            order: Order = await self._private_connectors[account_type].cancel_order(
                symbol=order_submit.symbol,
                order_id=order_id,
                **order_submit.kwargs,
            )
            order.uuid = order_submit.uuid
            if order.success:
                self._cache._order_status_update(order) # SOME STATUS -> CANCELING
                self._msgbus.send(endpoint="canceling", msg=order)
            else:
                # self._cache._order_status_update(order) # SOME STATUS -> FAILED
                self._msgbus.send(endpoint="cancel_failed", msg=order)

        else:
            self._log.error(
                f"Order ID not found for UUID: {order_submit.uuid}, The order may already be canceled or filled or not exist"
            )

    async def _handle_create_order(
        self, order_submit: OrderSubmit, account_type: AccountType
    ):
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
            self._cache._order_initialized(order) # INITIALIZED -> PENDING
            self._msgbus.send(endpoint="pending", msg=order)
        else:
            self._cache._order_status_update(order) # INITIALIZED -> FAILED
            self._msgbus.send(endpoint="failed", msg=order)

    async def _handle_submit_order(
        self, account_type: AccountType, queue: asyncio.Queue[OrderSubmit]
    ):
        self._log.debug(f"Handling orders for account type: {account_type}")
        while True:
            order_submit = await queue.get()
            self._log.debug(f"[ORDER SUBMIT]: {order_submit}")
            if order_submit.submit_type == SubmitType.CANCEL:
                await self._handle_cancel_order(order_submit, account_type)
            elif order_submit.submit_type == SubmitType.CREATE:
                await self._handle_create_order(order_submit, account_type)
            queue.task_done()

    async def start(self):
        self._log.debug("ExecutionManagementSystem started")

        # Start order submit handlers
        for account_type in self._order_submit_queues.keys():
            self._task_manager.create_task(
                self._handle_submit_order(account_type, self._order_submit_queues[account_type])
            )
