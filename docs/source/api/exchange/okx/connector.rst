nexustrader.exchange.okx.connector
=====================================

.. currentmodule:: nexustrader.exchange.okx.connector

This module implements WebSocket connectors for OKX exchange, providing both public and private data stream handling.

Public Connector
-----------------

.. autoclass:: OkxPublicConnector
   :members:
   :undoc-members:
   :show-inheritance:

   .. rubric:: Supported Channels

   Market Data Streams:
    * Trade Stream
    * Book Ticker Stream (BBO-TBT)
    * Candlestick Stream

   .. rubric:: Message Handlers

   * Trade Message Handler
   * Book Ticker Message Handler
   * Candlestick Message Handler

Private Connector
-----------------

.. autoclass:: OkxPrivateConnector
   :members:
   :undoc-members:
   :show-inheritance:

   .. rubric:: Supported Channels

   Account Data Streams:
    * Order Updates
    * Position Updates
    * Account Updates

   .. rubric:: Message Handlers

   * Order Message Handler
   * Position Message Handler
   * Account Message Handler

