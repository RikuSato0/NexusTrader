Bybit Exchange
===============

BybitPublicConnector
------------------

.. py:class:: BybitPublicConnector(account_type: BybitAccountType, exchange: BybitExchangeManager, msgbus: MessageBus, task_manager: TaskManager)

   Bybit implementation of public market data connector.

   :param BybitAccountType account_type: Account type for connection
   :param BybitExchangeManager exchange: Exchange manager instance
   :param MessageBus msgbus: Message bus for publishing data
   :param TaskManager task_manager: Task manager for async operations

   .. py:property:: market_type
      :type: str

      Get market type suffix for symbol mapping.

   .. py:method:: subscribe_trade(symbol: str)
      :async:

      Subscribe to trade data stream.

      :param str symbol: Trading pair symbol

   .. py:method:: subscribe_bookl1(symbol: str)
      :async:

      Subscribe to level 1 orderbook data.

      :param str symbol: Trading pair symbol

   .. py:method:: subscribe_kline(symbol: str, interval: str)
      :async:

      Subscribe to kline/candlestick data.

      :param str symbol: Trading pair symbol
      :param str interval: Kline interval

BybitPrivateConnector
-------------------

.. py:class:: BybitPrivateConnector(exchange: BybitExchangeManager, account_type: BybitAccountType, msgbus: MessageBus, rate_limit: Optional[RateLimit], task_manager: TaskManager)

   Bybit implementation of private trading connector.

   :param BybitExchangeManager exchange: Exchange manager instance
   :param BybitAccountType account_type: Account type for connection
   :param MessageBus msgbus: Message bus for order events
   :param Optional[RateLimit] rate_limit: Rate limit configuration
   :param TaskManager task_manager: Task manager for async operations

   .. py:method:: create_order(symbol: str, side: OrderSide, type: OrderType, amount: Decimal, price: Decimal, time_in_force: TimeInForce, position_side: PositionSide, **kwargs) -> Order
      :async:

      Create order on Bybit exchange.

      :param str symbol: Trading pair symbol
      :param OrderSide side: Order side (BUY/SELL)
      :param OrderType type: Order type (MARKET/LIMIT)
      :param Decimal amount: Order quantity
      :param Decimal price: Order price (for limit orders)
      :param TimeInForce time_in_force: Time in force
      :param PositionSide position_side: Position side
      :param kwargs: Additional Bybit-specific parameters
      :return: Created order object
      :rtype: Order

   .. py:method:: cancel_order(symbol: str, order_id: str, **kwargs) -> Order
      :async:

      Cancel order on Bybit exchange.

      :param str symbol: Trading pair symbol
      :param str order_id: Order ID to cancel
      :param kwargs: Additional Bybit-specific parameters
      :return: Canceled order object
      :rtype: Order

   .. py:method:: _get_category(market: BybitMarket) -> str

      Get Bybit category for market.

      :param BybitMarket market: Market data
      :return: Category string
      :rtype: str

BybitWSClient
-----------

.. py:class:: BybitWSClient(account_type: BybitAccountType, handler: Callable[..., Any], task_manager: TaskManager)

   WebSocket client for Bybit exchange.

   :param BybitAccountType account_type: Account type for connection
   :param Callable handler: Message handler function
   :param TaskManager task_manager: Task manager for async operations

   .. py:method:: subscribe_trade(symbol: str)
      :async:

      Subscribe to trade data stream.

      :param str symbol: Trading pair symbol

   .. py:method:: subscribe_orderbook(symbol: str, depth: int = 1)
      :async:

      Subscribe to orderbook data stream.

      :param str symbol: Trading pair symbol
      :param int depth: Orderbook depth level

   .. py:method:: subscribe_kline(symbol: str, interval: str)
      :async:

      Subscribe to kline/candlestick stream.

      :param str symbol: Trading pair symbol
      :param str interval: Kline interval

   .. py:method:: subscribe_user_data_stream(listen_key: str)
      :async:

      Subscribe to user data stream.

      :param str listen_key: Listen key for user data stream
