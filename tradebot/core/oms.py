import asyncio

from tradebot.types import Order
from tradebot.constants import OrderStatus
from tradebot.core.cache import AsyncCache
from tradebot.core.log import SpdLog
from tradebot.core.nautilius_core import MessageBus
from tradebot.core.entity import TaskManager

class OrderManagerSystem:
    def __init__(self, cache: AsyncCache, msgbus: MessageBus, task_manager: TaskManager):
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )
        self._cache = cache
        self._order_msg_queue: asyncio.Queue[Order] = asyncio.Queue()
        self._position_msg_queue: asyncio.Queue[Order] = asyncio.Queue()    
        self._msgbus = msgbus
        self._task_manager = task_manager
        self._msgbus.subscribe(topic="order", handler=self.add_order_msg)
        self._msgbus.subscribe(topic="order", handler=self.add_position_msg)
        
    def add_order_msg(self, order: Order):
        self._order_msg_queue.put_nowait(order)

    def add_position_msg(self, order: Order):
        self._position_msg_queue.put_nowait(order)
    
    async def handle_position_event(self):
        while True:
            try:
                order = await self._position_msg_queue.get()
                self._cache.apply_position(order)
                self._position_msg_queue.task_done()
            except Exception as e:
                self._log.error(f"Error in handle_position_event: {e}")

    async def handle_order_event(self):
        while True:
            try:
                order = await self._order_msg_queue.get()
                match order.status:
                    case OrderStatus.PENDING:
                        self._log.debug(f"ORDER STATUS PENDING: {str(order)}")
                        self._cache.order_initialized(order)
                    case OrderStatus.CANCELING:
                        self._log.debug(f"ORDER STATUS CANCELING: {str(order)}")
                        self._cache.order_status_update(order)
                    case OrderStatus.ACCEPTED:
                        self._log.debug(f"ORDER STATUS ACCEPTED: {str(order)}")
                        self._cache.order_status_update(order)
                        self._msgbus.send(endpoint="accepted", msg=order)
                    case OrderStatus.PARTIALLY_FILLED:
                        self._log.debug(f"ORDER STATUS PARTIALLY FILLED: {str(order)}")
                        self._cache.order_status_update(order)
                        self._msgbus.send(endpoint="partially_filled", msg=order)
                    case OrderStatus.CANCELED:
                        self._log.debug(f"ORDER STATUS CANCELED: {str(order)}")
                        self._cache.order_status_update(order)
                        self._msgbus.send(endpoint="canceled", msg=order)
                    case OrderStatus.FILLED:
                        self._log.debug(f"ORDER STATUS FILLED: {str(order)}")
                        self._cache.order_status_update(order)
                        self._msgbus.send(endpoint="filled", msg=order)
                    case OrderStatus.EXPIRED:
                        self._log.debug(f"ORDER STATUS EXPIRED: {str(order)}")
                        self._cache.order_status_update(order)
                self._order_msg_queue.task_done()
            except Exception as e:
                self._log.error(f"Error in handle_order_event: {e}")
    
    async def start(self):
        self._log.debug("OrderManagerSystem started")
        self._task_manager.create_task(self.handle_order_event())
        self._task_manager.create_task(self.handle_position_event())



