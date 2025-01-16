import asyncio
from collections import defaultdict
from typing import Optional
from nexustrader.core.log import SpdLog
from nexustrader.schema import Order

class OrderRegistry:
    def __init__(self):
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )
        self._uuid_to_order_id = {}
        self._order_id_to_uuid = {}
        self._uuid_init_events = defaultdict(asyncio.Event)

    def register_order(self, order: Order) -> None:
        """Register a new order ID to UUID mapping"""
        self._order_id_to_uuid[order.id] = order.uuid
        self._uuid_to_order_id[order.uuid] = order.id
        self._uuid_init_events[order.id].set() # the order id is linked to the order submit uuid
        self._log.debug(f"[ORDER REGISTER]: linked order id {order.id} with uuid {order.uuid}")

    def get_order_id(self, uuid: str) -> Optional[str]:
        """Get order ID by UUID"""
        return self._uuid_to_order_id.get(uuid, None)

    def get_uuid(self, order_id: str) -> Optional[str]:
        """Get UUID by order ID"""
        return self._order_id_to_uuid.get(order_id, None)

    async def wait_for_order_id(self, order_id: str) -> None:
        """Wait for an order ID to be registered"""
        await self._uuid_init_events[order_id].wait()

    def remove_order(self, order: Order) -> None:
        """Remove order mapping when no longer needed"""
        self._order_id_to_uuid.pop(order.id, None)
        self._uuid_to_order_id.pop(order.uuid, None)
        self._uuid_init_events.pop(order.id, None)
