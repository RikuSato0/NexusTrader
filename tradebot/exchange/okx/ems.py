import asyncio
from decimal import Decimal
from typing import Dict
from tradebot.constants import AccountType
from tradebot.schema import OrderSubmit
from tradebot.core.cache import AsyncCache
from tradebot.core.nautilius_core import MessageBus
from tradebot.core.entity import TaskManager
from tradebot.core.registry import OrderRegistry
from tradebot.exchange.okx import OkxAccountType
from tradebot.exchange.okx.schema import OkxMarket
from tradebot.base import ExecutionManagementSystem


class OkxExecutionManagementSystem(ExecutionManagementSystem):
    _market: Dict[str, OkxMarket]

    OKX_ACCOUNT_TYPE_PRIORITY = [
        OkxAccountType.DEMO,
        OkxAccountType.AWS,
        OkxAccountType.LIVE,
    ]
    
    def __init__(
        self,
        market: Dict[str, OkxMarket],
        cache: AsyncCache,
        msgbus: MessageBus,
        task_manager: TaskManager,
        registry: OrderRegistry,
    ):
        super().__init__(
            market=market,
            cache=cache,
            msgbus=msgbus,
            task_manager=task_manager,
            registry=registry,
        )
        self._okx_account_type: OkxAccountType = None

    def _build_order_submit_queues(self):
        for account_type in self._private_connectors.keys():
            if isinstance(account_type, OkxAccountType):
                self._order_submit_queues[account_type] = asyncio.Queue()
                break

    def _set_account_type(self):
        account_types = self._private_connectors.keys()
        for account_type in self.OKX_ACCOUNT_TYPE_PRIORITY:
            if account_type in account_types:
                self._okx_account_type = account_type
                break

    def _submit_order(
        self, order: OrderSubmit, account_type: AccountType | None = None
    ):
        if not account_type:
            account_type = self._okx_account_type
        self._order_submit_queues[account_type].put_nowait(order)

    def _get_min_order_amount(self, symbol: str, market: OkxMarket) -> Decimal:
        pass
