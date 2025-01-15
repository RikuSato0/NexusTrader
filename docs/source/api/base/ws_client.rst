tradebot.base.ws_client
========================

.. currentmodule:: tradebot.base.ws_client

This module contains the WSClient class, which is responsible for managing WebSocket connections and message handling.

Class Overview
-----------------

.. autoclass:: Listener
   :members: __init__, send_user_specific_ping, on_ws_connected, on_ws_disconnected, on_ws_frame
   :undoc-members:
   :show-inheritance:

.. autoclass:: WSClient
   :members: __init__, connected, connect, disconnect, _connect, _connection_handler, _send, _msg_handler
   :undoc-members:
   :show-inheritance:
