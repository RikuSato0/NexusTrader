tradebot.exchange.binance.oms
=====================================

.. currentmodule:: tradebot.exchange.binance.oms

This module implements the Order Management System (OMS) for Binance exchange, handling order processing and position tracking.

Class Overview
-----------------

.. autoclass:: BinanceOrderManagementSystem
   :members:
   :undoc-members:
   :show-inheritance:

   .. rubric:: Dependencies

   The BinanceOrderManagementSystem requires the following components:

   * AsyncCache - For caching order and position data
   * MessageBus - For handling order and position messages
   * TaskManager - For managing asynchronous tasks
   * OrderRegistry - For maintaining order records

   .. rubric:: Message Topics

   Subscribes to the following message topics:

   * ``binance.order`` - For order updates
   * ``binance.position`` - For position updates
