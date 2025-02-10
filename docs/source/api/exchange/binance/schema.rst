nexustrader.exchange.binance.schema
=====================================

.. currentmodule:: nexustrader.exchange.binance.schema

This module defines the data structures and models used for Binance exchange API responses. It provides type-safe data models for market data, orders, trades, and other exchange-specific data structures.

Market Data Models
--------------------------

.. autoclass:: BinanceMarket
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: BinanceMarketInfo
   :members:
   :undoc-members:
   :show-inheritance:

Order Models
---------------------------

.. autoclass:: BinanceOrder
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: BinanceUserTrade
   :members:
   :undoc-members:
   :show-inheritance:

Account Models
---------------------------

.. autoclass:: BinanceSpotAccountInfo
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: BinanceFuturesAccountInfo
   :members:
   :undoc-members:
   :show-inheritance:

WebSocket Message Models
---------------------------

.. autoclass:: BinanceSpotOrderUpdateMsg
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: BinanceFuturesOrderUpdateMsg
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: BinanceFuturesUpdateMsg
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: BinanceMarkPrice
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: BinanceKline
   :members:
   :undoc-members:
   :show-inheritance:

See Also
---------------------------

* :doc:`rest_api` - REST API implementation
* :doc:`websockets` - WebSocket client
* :doc:`exchange` - Exchange management
