tradebot.exchange.okx.websockets
=====================================

.. currentmodule:: tradebot.exchange.okx.websockets

This module implements the WebSocket client for OKX exchange, providing both public and private data stream functionality.

Class Overview
----------------------------------

.. autoclass:: OkxWSClient
   :members:
   :undoc-members:
   :show-inheritance:

   .. rubric:: Public Channels

   Market Data Streams:
    * Order Book Updates (``books``, ``books5``, ``bbo-tbt``, ``books-l2-tbt``, ``books50-l2-tbt``)
    * Trade Updates
    * Candlestick Data

   .. rubric:: Private Channels

   Account and Trading Streams:
    * Account Updates
    * Position Updates
    * Order Updates
    * Trade Fill Updates

WebSocket Subscriptions
----------------------------------

Public Channels
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. method:: subscribe_order_book(symbol: str, channel: str)

   Subscribe to order book updates.

   :param symbol: Trading pair symbol
   :param channel: Order book channel type (``books``, ``books5``, ``bbo-tbt``, etc.)

.. method:: subscribe_trade(symbol: str)

   Subscribe to trade updates.

   :param symbol: Trading pair symbol

.. method:: subscribe_candlesticks(symbol: str, interval: str)

   Subscribe to candlestick data.

   :param symbol: Trading pair symbol
   :param interval: Time interval (``1m``, ``3m``, ``5m``, etc.)

Private Channels
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. method:: subscribe_account()

   Subscribe to account updates.

.. method:: subscribe_positions(inst_type: str = "ANY")

   Subscribe to position updates.

   :param inst_type: Instrument type (``MARGIN``, ``SWAP``, ``FUTURES``, etc.)

.. method:: subscribe_orders(inst_type: str = "ANY")

   Subscribe to order updates.

   :param inst_type: Instrument type

Authentication
--------------------------

The client supports API key authentication with:

* API Key
* Secret Key
* Passphrase
* Automatic authentication renewal
* Support for demo/live environments
