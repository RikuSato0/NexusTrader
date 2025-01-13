tradebot.core.entity
=====================

.. currentmodule:: tradebot.core.entity

This module contains classes and functions for managing tasks, events, and data readiness in the trading system.

Class Overview
-----------------

.. autoclass:: RateLimit
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: TaskManager
   :members: __init__, create_task, cancel_task, wait, cancel
   :undoc-members:
   :show-inheritance:

.. autoclass:: RedisClient
   :members: get_client, get_async_client
   :undoc-members:
   :show-inheritance:

.. autoclass:: Clock
   :members: __init__, add_tick_callback, run
   :undoc-members:
   :show-inheritance:

.. autoclass:: ZeroMQSignalRecv
   :members: __init__, start
   :undoc-members:
   :show-inheritance:

.. autoclass:: DataReady
   :members: __init__, input, ready
   :undoc-members:
   :show-inheritance:

