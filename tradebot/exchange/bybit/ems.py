import asyncio
import warnings
from typing import Dict, List, Tuple
from decimal import Decimal
from tradebot.constants import AccountType
from tradebot.schema import OrderSubmit
from tradebot.core.cache import AsyncCache
from tradebot.core.nautilius_core import MessageBus
from tradebot.core.entity import TaskManager
from tradebot.core.registry import OrderRegistry
from tradebot.exchange.bybit import BybitAccountType
from tradebot.exchange.bybit.schema import BybitMarket
from tradebot.base import ExecutionManagementSystem


class BybitExecutionManagementSystem(ExecutionManagementSystem):
    _market: Dict[str, BybitMarket]

    def __init__(
        self,
        market: Dict[str, BybitMarket],
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
        self._bybit_account_type: BybitAccountType = None

    def _build_order_submit_queues(self):
        for account_type in self._private_connectors.keys():
            if isinstance(account_type, BybitAccountType):
                self._order_submit_queues[account_type] = asyncio.Queue()

    def _set_account_type(self):
        account_types = self._private_connectors.keys()
        self._bybit_account_type = (
            BybitAccountType.ALL_TESTNET
            if BybitAccountType.ALL_TESTNET in account_types
            else BybitAccountType.ALL
        )

    def _submit_order(
        self, order: OrderSubmit, account_type: AccountType | None = None
    ):
        if not account_type:
            account_type = self._bybit_account_type
        self._order_submit_queues[account_type].put_nowait(order)
        
    def _calculate_twap_orders(self, order_submit: OrderSubmit) -> Tuple[List[Decimal], float]:
        amount_list = []
        symbol = order_submit.instrument_id.symbol
        total_amount = float(order_submit.amount)
        wait = order_submit.wait
        duration = order_submit.duration
        
        book = self._cache.bookl1(symbol)
        min_order_amount = 20 / (book.bid + book.ask)        
        
        interval = duration // wait
        if total_amount < min_order_amount:
            warnings.warn(f"Amount {total_amount} is less than min order amount {min_order_amount}. No need to split orders.")
            wait = 0
            return [self._amount_to_precision(symbol, min_order_amount)], wait
        
        base_amount = total_amount / interval
        
        while base_amount < min_order_amount and interval > 1:
            interval -= 1
            base_amount = total_amount / interval
        
        base_amount = self._amount_to_precision(symbol, base_amount)
        
        interval = total_amount // float(base_amount)
        remaining = total_amount - interval * float(base_amount)
        
        if remaining < min_order_amount:
            amount_list = [base_amount] * interval 
            amount_list[-1] += Decimal(str(remaining))
        else:
            amount_list = [base_amount] * interval + [Decimal(str(remaining))]
        
        wait = duration / len(amount_list)
        return amount_list, wait
