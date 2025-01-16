nexustrader.core.registry
===============================

.. currentmodule:: nexustrader.core.registry

The OrderRegistry class is used to manage the mapping relationship between order IDs and UUIDs. In the trading system, each order has two identifiers:

- ``UUID``: internally generated unique identifier
- ``order_id``: order ID returned by the exchange

Class Overview
-----------------

.. autoclass:: OrderRegistry
   :members: register_order, get_order_id, get_uuid, wait_for_order_id, remove_order
   :undoc-members:
   :show-inheritance:
