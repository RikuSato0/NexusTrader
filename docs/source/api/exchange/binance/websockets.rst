tradebot.exchange.binance.websockets
=====================================

.. currentmodule:: tradebot.exchange.binance.websockets

This module implements WebSocket client for Binance exchange, providing real-time market data and user data streams.

Available WebSocket URLs:
 - Spot: ``wss://stream.binance.com:9443/ws``
 - USD-M Futures: ``wss://fstream.binance.com/ws``
 - COIN-M Futures: ``wss://dstream.binance.com/ws``

Class Overview
-----------------

.. autoclass:: BinanceWSClient
   :members:
   :undoc-members:
   :show-inheritance:

   .. rubric:: Supported Streams

   Market Data Streams:
    * Aggregate Trade Stream
    * Trade Stream
    * Book Ticker Stream
    * Mark Price Stream (Futures only)
    * Kline/Candlestick Stream

   User Data Streams:
    * Account Updates
    * Order Updates
    * Position Updates (Futures only)

See Also
-----------------

* :doc:`rest_api` - REST API implementation
* :doc:`exchange` - Exchange management
* :doc:`schema` - Data models
