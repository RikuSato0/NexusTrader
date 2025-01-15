tradebot.exchange.bybit.websockets
=====================================

.. currentmodule:: tradebot.exchange.bybit.websockets

The Bybit WebSocket client provides real-time market data and trading information through WebSocket connections. It supports both public and private channels with automatic authentication and rate limiting.

Class Overview
-----------------

.. autoclass:: BybitWSClient
   :members:
   :undoc-members:
   :show-inheritance:

WebSocket Channels
---------------------

Public Channels
~~~~~~~~~~~~~~~~~~~~~

orderbook
^^^^^^^^^
**Push Frequencies:**

- Linear & Inverse:
    - Level 1: 10ms
    - Level 50: 20ms
    - Level 200/500: 100ms
- Spot:
    - Level 1: 10ms
    - Level 50: 20ms
    - Level 200: 200ms
- Option:
    - Level 25: 20ms
    - Level 100: 100ms

trade
^^^^^
Real-time trade data for specified symbols.

ticker
^^^^^^
Real-time price and trading data updates.

kline
^^^^^
Candlestick data with available intervals:

- Minutes: 1, 3, 5, 15, 30
- Hours: 1 (60), 2 (120), 4 (240), 6 (360), 12 (720)

Private Channels
~~~~~~~~~~~~~~~~~~~~~

order
^^^^^
Order updates with topics:

- All-in-one: ``order``
- Category specific: ``order.spot``, ``order.linear``, ``order.inverse``, ``order.option``

position
^^^^^^^^
Position updates with topics:

- All-in-one: ``position``
- Category specific: ``position.linear``, ``position.inverse``, ``position.option``

wallet
^^^^^^
Wallet balance updates with topic: ``wallet``
