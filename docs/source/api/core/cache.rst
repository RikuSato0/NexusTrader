Cache Module
============

.. automodule:: tradebot.core.cache
   :members:
   :undoc-members:
   :show-inheritance:

Overview
--------

The cache module provides Redis-based caching functionality for the trading bot.
It handles caching of market data, orders, positions and other trading-related information.

Key Components
--------------

- RedisCache: Main cache implementation using Redis
- CacheKey: Enum of cache key types
- CacheManager: High-level cache management interface

Usage Example
-------------

.. code-block:: python

   from tradebot.core.cache import RedisCache
   
   # Initialize cache
   cache = RedisCache()
   
   # Cache market data
   await cache.set_market_data("BTCUSDT", data)
   
   # Get cached data
   data = await cache.get_market_data("BTCUSDT")
