tradebot.exchange.okx.exchange
=====================================

.. currentmodule:: tradebot.exchange.okx.exchange

This module implements the exchange manager for OKX, handling market data loading and symbol management.

Class Overview
-----------------

.. autoclass:: OkxExchangeManager
   :members:
   :undoc-members:
   :show-inheritance:

   .. rubric:: Key Features

   * Market data loading and caching
   * Symbol mapping and normalization
   * Support for spot, linear futures, inverse futures markets
   * Automatic market type detection
   * Exchange-specific configuration management

   .. rubric:: Market Types

   Supports the following market types:
    * Spot Markets
    * Linear Futures
    * Inverse Futures
    * Perpetual Swaps

   Options markets are currently not supported.

Configuration
-----------------

.. code-block:: python

   config = {
       "exchange_id": "okx",  # Optional, defaults to "okx"
       "password": "your_passphrase",  # Optional, API passphrase
       # ... other configuration options
   }

