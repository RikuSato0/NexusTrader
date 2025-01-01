from tradebot.base import OrderManagementSystem
from tradebot.core.cache import AsyncCache
from tradebot.core.nautilius_core import MessageBus
from tradebot.core.entity import TaskManager
from tradebot.core.registry import OrderRegistry


class BybitOrderManagementSystem(OrderManagementSystem):
    def __init__(
        self,
        cache: AsyncCache,
        msgbus: MessageBus,
        task_manager: TaskManager,
        registry: OrderRegistry,
    ):
        super().__init__(cache, msgbus, task_manager, registry)
        self._msgbus.register(endpoint="bybit.order", handler=self._add_order_msg)

    #TODO: some rest-api check logic
