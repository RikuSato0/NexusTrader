tradebot.exchange.okx.schema
=====================================

.. currentmodule:: tradebot.exchange.okx.schema

This module defines data structures and models for OKX exchange API responses and WebSocket messages.

WebSocket Message Models
-----------------------

.. autoclass:: OkxWsGeneralMsg
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: OkxWsBboTbtMsg
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: OkxWsCandleMsg
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: OkxWsTradeMsg
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: OkxWsOrderMsg
   :members:
   :undoc-members:
   :show-inheritance:

REST API Response Models
-----------------------

Order Related
^^^^^^^^^^^^^

.. autoclass:: OkxPlaceOrderResponse
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: OkxCancelOrderResponse
   :members:
   :undoc-members:
   :show-inheritance:

Account Related
^^^^^^^^^^^^^^

.. autoclass:: OkxBalanceResponse
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: OkxPositionResponse
   :members:
   :undoc-members:
   :show-inheritance:

Market Data Models
-----------------

.. autoclass:: OkxMarket
   :members:
   :undoc-members:
   :show-inheritance:

   Represents market information for an instrument on OKX.

   Example market data::

      {
          "id": "BTC-USDT-SWAP",
          "symbol": "BTC/USDT:USDT",
          "base": "BTC",
          "quote": "USDT",
          "type": "swap",
          "linear": true,
          "inverse": false,
          "active": true,
          ...
      }

Error Response Models
-------------------

.. autoclass:: OkxErrorResponse
   :members:
   :undoc-members:
   :show-inheritance:
