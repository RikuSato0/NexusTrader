Order Management System
====================

.. automodule:: tradebot.core.oms
   :members:
   :undoc-members:
   :show-inheritance:

Overview
--------

The Order Management System (OMS) module handles order lifecycle management,
position tracking, and risk management across multiple exchanges.

Key Components
-------------

- OrderManager: Central order management system
- PositionManager: Tracks and manages trading positions
- RiskManager: Handles risk calculations and limits

Usage Example
------------

.. code-block:: python

   from tradebot.core.oms import OrderManager
   
   # Initialize OMS
   oms = OrderManager()
   
   # Create order
   order = await oms.create_order(
       exchange="binance",
       symbol="BTCUSDT",
       side="buy",
       amount=0.1,
       price=50000
   )
   
   # Track order status
   status = await oms.get_order_status(order.id) 
