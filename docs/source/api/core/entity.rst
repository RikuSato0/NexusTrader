Entity Module
============

.. automodule:: tradebot.core.entity
   :members:
   :undoc-members:
   :show-inheritance:

Overview
--------

The entity module provides base classes and utilities for managing trading entities
like orders, positions, and market data.

Key Components
-------------

- EventSystem: Base event handling system
- Entity: Base class for all trading entities
- EntityManager: Manages collections of trading entities

Usage Example
------------

.. code-block:: python

   from tradebot.core.entity import EventSystem
   
   class MySystem(EventSystem):
       def __init__(self):
           super().__init__()
           self.register_event("order_update")
       
       async def on_order_update(self, order):
           # Handle order update
           pass 
