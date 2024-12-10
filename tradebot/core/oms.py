import asyncio

from tradebot.types import Order
from tradebot.constants import OrderStatus
from tradebot.core.cache import AsyncCache
from tradebot.core.log import SpdLog
from tradebot.core.nautilius_core import MessageBus

class OrderManagerSystem:
    def __init__(self, cache: AsyncCache, msgbus: MessageBus):
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )
        self._cache = cache
        self._order_msg_queue: asyncio.Queue[Order] = asyncio.Queue()
        self._msgbus = msgbus
    def add_order_msg(self, order: Order):
        self._order_msg_queue.put_nowait(order)

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
                await self._cache.apply_position(order)
                self._order_msg_queue.task_done()
            except Exception as e:
                self._log.error(f"Error in handle_order_event: {e}")
