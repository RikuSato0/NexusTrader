OrderRegistry Module
=====================

.. currentmodule:: tradebot.core.registry

The OrderRegistry class is used to manage the mapping relationship between order IDs and UUIDs. In the trading system, each order has two identifiers:

- UUID: internally generated unique identifier
- order_id: order ID returned by the exchange

Class Overview
-----------------

.. autoclass:: OrderRegistry
   :members: register_order, get_order_id, get_uuid, wait_for_order_id, remove_order
   :undoc-members:
   :show-inheritance:

Usage Example
-----------------

Here is a basic usage example of OrderRegistry:

.. code-block:: python

    from tradebot.core.registry import OrderRegistry
    from tradebot.schema import Order

    # Create a registry instance
    registry = OrderRegistry()

    # Register a new order
    order = Order(id="exchange_order_123", uuid="internal_uuid_456")
    registry.register_order(order)

    # Get order ID
    order_id = registry.get_order_id("internal_uuid_456")  # Returns "exchange_order_123"

    # Get UUID
    uuid = registry.get_uuid("exchange_order_123")  # Returns "internal_uuid_456"

    # Asynchronously wait for order ID registration
    await registry.wait_for_order_id("exchange_order_123")

    # Remove order mapping
    registry.remove_order(order)

Key Features
-----------------

1. Bi-directional Mapping
   - Supports querying order ID by UUID
   - Supports querying UUID by order ID

2. Asynchronous Support
   - Provides an asynchronous waiting mechanism for waiting for order ID registration

3. Thread Safety
   - Uses asyncio.Event to ensure thread-safe operations

4. Log Recording
   - Integrates detailed log recording capabilities

Notes
-----------------

- Order registration triggers the corresponding Event immediately
- Removing an order simultaneously cleans up all related mappings and events
- Returns None instead of throwing an exception when getting a non-existent mapping


