tradebot.exchange.okx.oms
=====================================

.. currentmodule:: tradebot.exchange.okx.oms

This module implements the Order Management System (OMS) for OKX exchange, handling order tracking and status management.

Class Overview
-----------------

.. autoclass:: OkxOrderManagementSystem
   :members:
   :undoc-members:
   :show-inheritance:

   .. rubric:: Key Features

   * Order message handling and processing
   * Order status tracking
   * Integration with message bus system
   * Asynchronous order cache management
   * Order registry integration

   .. rubric:: Message Bus Integration

   Automatically registers for order messages on the "okx.order" endpoint.

Implementation Notes
-------------------------------

The OMS is responsible for:
 * Tracking order lifecycle
 * Processing order updates
 * Maintaining order state
 * Synchronizing with order registry
 * Caching order information

