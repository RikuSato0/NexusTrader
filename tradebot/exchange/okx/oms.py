from tradebot.base import OrderManagementSystem
from tradebot.core.cache import AsyncCache
from tradebot.core.nautilius_core import MessageBus
from tradebot.core.entity import TaskManager
from tradebot.core.registry import OrderRegistry


class OkxOrderManagementSystem(OrderManagementSystem):
    def __init__(
        self,
        cache: AsyncCache,
        msgbus: MessageBus,
        task_manager: TaskManager,
        registry: OrderRegistry,
    ):
        super().__init__(cache, msgbus, task_manager, registry)
        self._msgbus.subscribe(topic="okx.order", handler=self._add_order_msg)
        self._msgbus.subscribe(topic="okx.spot.position", handler=self._handle_spot_position_event)
        self._msgbus.subscribe(topic="okx.future.position", handler=self._handle_future_position_event)

    #TODO: some rest-api check logic
