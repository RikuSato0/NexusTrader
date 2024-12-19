import asyncio
from tradebot.schema import Order
from tradebot.constants import OrderStatus
from tradebot.core.cache import AsyncCache
from tradebot.core.registry import OrderRegistry
from tradebot.core.log import SpdLog
from tradebot.core.nautilius_core import MessageBus
from tradebot.core.entity import TaskManager


class OrderManagementSystem:

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
        self._position_msg_queue: asyncio.Queue[Order] = asyncio.Queue()

        # Set up message bus subscriptions
        self._msgbus.subscribe(topic="order", handler=self._add_order_msg)
        self._msgbus.subscribe(topic="order", handler=self._add_position_msg)
        

    def _add_order_msg(self, order: Order):
        self._order_msg_queue.put_nowait(order)

    def _add_position_msg(self, order: Order):
        self._position_msg_queue.put_nowait(order)

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
        self._task_manager.create_task(self._handle_position_event())
