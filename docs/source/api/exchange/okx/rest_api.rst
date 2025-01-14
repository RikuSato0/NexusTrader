tradebot.exchange.okx.rest_api
=====================================

.. currentmodule:: tradebot.exchange.okx.rest_api

This module implements the REST API client for OKX exchange, providing methods to interact with various OKX API endpoints.

Class Overview
-----------------

.. autoclass:: OkxApiClient
   :members:
   :undoc-members:
   :show-inheritance:

   .. rubric:: Key Features

   * Asynchronous API requests
   * Automatic request signing
   * Rate limiting support
   * Error handling
   * Response parsing

API Methods
-----------------

Account Endpoints
^^^^^^^^^^^^^^^^^^^^^^^

.. method:: get_api_v5_account_balance(ccy: str | None = None)

   Get account balance information.

   :param ccy: Currency code (optional)
   :return: Account balance response

.. method:: get_api_v5_account_positions(inst_type: str | None = None, inst_id: str | None = None, pos_id: str | None = None)

   Get position information.

   :param inst_type: Instrument type
   :param inst_id: Instrument ID
   :param pos_id: Position ID
   :return: Position response

Trading Endpoints
^^^^^^^^^^^^^^^^^^^^^^^

.. method:: post_api_v5_trade_order(inst_id: str, td_mode: str, side: str, ord_type: str, sz: str, **kwargs)

   Place a new order.

   :param inst_id: Instrument ID
   :param td_mode: Trading mode
   :param side: Order side
   :param ord_type: Order type
   :param sz: Order size
   :return: Order placement response

.. method:: post_api_v5_trade_cancel_order(inst_id: str, ord_id: str | None = None, cl_ord_id: str | None = None)

   Cancel an existing order.

   :param inst_id: Instrument ID
   :param ord_id: Order ID
   :param cl_ord_id: Client order ID
   :return: Order cancellation response

Authentication
-----------------

The client supports both API key and signature-based authentication:

* API Key authentication
* Timestamp-based signatures
* Optional testnet support
* Passphrase requirement

