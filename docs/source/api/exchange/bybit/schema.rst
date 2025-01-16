nexustrader.exchange.bybit.schema
=====================================

.. currentmodule:: nexustrader.exchange.bybit.schema

This module defines the data structures and schemas used for Bybit API responses and WebSocket messages. It includes market data structures, order types, position information, and wallet balance schemas.

Constants
-----------------
.. data:: BYBIT_PONG
   :type: str
   
   WebSocket pong message constant

Class Overview
-----------------

Market Data
~~~~~~~~~~~~~~~
.. autoclass:: BybitMarket
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: BybitMarketInfo
   :members:
   :undoc-members:

Order Related
~~~~~~~~~~~~~~~
.. autoclass:: BybitOrder
   :members:
   :undoc-members:

.. autoclass:: BybitOrderResult
   :members:
   :undoc-members:

.. autoclass:: BybitOrderResponse
   :members:
   :undoc-members:

Position Related
~~~~~~~~~~~~~~~~~
.. autoclass:: BybitPositionStruct
   :members:
   :undoc-members:

.. autoclass:: BybitPositionResponse
   :members:
   :undoc-members:

WebSocket Messages
~~~~~~~~~~~~~~~~~~~~~
.. autoclass:: BybitWsMessageGeneral
   :members:
   :undoc-members:

.. autoclass:: BybitWsOrderbookDepth
   :members:
   :undoc-members:

.. autoclass:: BybitWsTrade
   :members:
   :undoc-members:

.. autoclass:: BybitWsOrder
   :members:
   :undoc-members:

Balance Related
~~~~~~~~~~~~~~~~~~~~
.. autoclass:: BybitWalletBalance
   :members:
   :undoc-members:

.. autoclass:: BybitCoinBalance
   :members:
   :undoc-members:
