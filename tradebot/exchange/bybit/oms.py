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
        self._msgbus.register(endpoint="bybit.spot.position", handler=self._handle_spot_position_event)
        self._msgbus.register(endpoint="bybit.future.position", handler=self._handle_future_position_event)

    #TODO: some rest-api check logic
