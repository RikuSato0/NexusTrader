Binance Exchange
=================

BinanceExchangeManager
--------------------

.. py:class:: BinanceExchangeManager(config: Dict[str, Any] = None)

   Binance-specific implementation of ExchangeManager.

   :param Optional[Dict[str,Any]] config: Configuration dictionary

   .. py:method:: parse_symbol(bm: BinanceMarket) -> str

      Parse exchange market data into standardized symbol format.

      :param BinanceMarket bm: Binance market data
      :return: Standardized symbol string
      :rtype: str

   .. py:method:: load_markets()

      Load and parse Binance market data.
      
      Handles:
      - Spot markets
      - Future markets
      - Linear perpetual markets
      - Inverse perpetual markets

BinancePublicConnector
--------------------

.. py:class:: BinancePublicConnector(account_type: BinanceAccountType, exchange: BinanceExchangeManager, msgbus: MessageBus, task_manager: TaskManager)

   Binance implementation of public market data connector.

   :param BinanceAccountType account_type: Account type for connection
   :param BinanceExchangeManager exchange: Exchange manager instance
   :param MessageBus msgbus: Message bus for publishing data
   :param TaskManager task_manager: Task manager for async operations

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

BinancePrivateConnector
---------------------

.. py:class:: BinancePrivateConnector(exchange: BinanceExchangeManager, account_type: BinanceAccountType, msgbus: MessageBus, rate_limit: Optional[RateLimit], task_manager: TaskManager)

   Binance implementation of private trading connector.

   :param BinanceExchangeManager exchange: Exchange manager instance
   :param BinanceAccountType account_type: Account type for connection
   :param MessageBus msgbus: Message bus for order events
   :param Optional[RateLimit] rate_limit: Rate limit configuration
   :param TaskManager task_manager: Task manager for async operations

   .. py:method:: create_order(symbol: str, side: OrderSide, type: OrderType, amount: Decimal, price: Decimal, time_in_force: TimeInForce, position_side: PositionSide, **kwargs) -> Order
      :async:

      Create order on Binance exchange.

      :param str symbol: Trading pair symbol
      :param OrderSide side: Order side (BUY/SELL)
      :param OrderType type: Order type (MARKET/LIMIT)
      :param Decimal amount: Order quantity
      :param Decimal price: Order price (for limit orders)
      :param TimeInForce time_in_force: Time in force
      :param PositionSide position_side: Position side
      :param kwargs: Additional Binance-specific parameters
      :return: Created order object
      :rtype: Order

   .. py:method:: cancel_order(symbol: str, order_id: str, **kwargs) -> Order
      :async:

      Cancel order on Binance exchange.

      :param str symbol: Trading pair symbol
      :param str order_id: Order ID to cancel
      :param kwargs: Additional Binance-specific parameters
      :return: Canceled order object
      :rtype: Order

BinanceWSClient
-------------

.. py:class:: BinanceWSClient(account_type: BinanceAccountType, handler: Callable[..., Any], task_manager: TaskManager)

   WebSocket client for Binance exchange.

   :param BinanceAccountType account_type: Account type for connection
   :param Callable handler: Message handler function
   :param TaskManager task_manager: Task manager for async operations

   .. py:method:: subscribe_agg_trade(symbol: str)
      :async:

      Subscribe to aggregated trade stream.

      :param str symbol: Trading pair symbol

   .. py:method:: subscribe_trade(symbol: str)
      :async:

      Subscribe to raw trade stream.

      :param str symbol: Trading pair symbol

   .. py:method:: subscribe_book_ticker(symbol: str)
      :async:

      Subscribe to best bid/ask ticker stream.

      :param str symbol: Trading pair symbol

   .. py:method:: subscribe_mark_price(symbol: str, interval: Literal["1s", "3s"] = "1s")
      :async:

      Subscribe to mark price stream (futures only).

      :param str symbol: Trading pair symbol
      :param str interval: Update interval

   .. py:method:: subscribe_user_data_stream(listen_key: str)
      :async:

      Subscribe to user data stream.

      :param str listen_key: Listen key for user data stream

   .. py:method:: subscribe_kline(symbol: str, interval: str)
      :async:

      Subscribe to kline/candlestick stream.

      :param str symbol: Trading pair symbol
      :param str interval: Kline interval
