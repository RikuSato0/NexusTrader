Exchange Modules
==============

.. toctree::
   :maxdepth: 2

   binance
   bybit
   okx

Binance
-------

.. automodule:: tradebot.exchange.binance
   :members:
   :undoc-members:
   :show-inheritance:

Bybit
-----

.. automodule:: tradebot.exchange.bybit
   :members:
   :undoc-members:
   :show-inheritance:

OKX
---

.. automodule:: tradebot.exchange.okx
   :members:
   :undoc-members:
   :show-inheritance: 

TradingBot API Documentation
===========================

ExchangeManager
--------------

.. py:class:: ExchangeManager(config: Dict[str, Any])

   Base class for managing exchange connections and market data.

   :param dict config: Configuration dictionary containing exchange settings
   :param str config['apiKey']: API key for authentication
   :param str config['secret']: Secret key for authentication  
   :param bool config['sandbox']: Whether to use testnet/sandbox mode
   :param str config['exchange_id']: Exchange identifier (e.g. "binance", "bybit")

   .. py:property:: linear
      :type: List[str]

      Returns list of linear perpetual market symbols

   .. py:property:: inverse  
      :type: List[str]

      Returns list of inverse perpetual market symbols

   .. py:property:: spot
      :type: List[str] 

      Returns list of spot market symbols

   .. py:property:: future
      :type: List[str]

      Returns list of futures market symbols

   .. py:method:: load_markets()

      Load market data from exchange.
      Must be implemented by subclasses.

WSClient
--------

.. py:class:: WSClient(url: str, limiter: AsyncLimiter, handler: Callable, task_manager: TaskManager, **kwargs)

   Base WebSocket client for exchange connections.

   :param str url: WebSocket endpoint URL
   :param AsyncLimiter limiter: Rate limiter for API calls
   :param Callable handler: Callback function for handling messages
   :param TaskManager task_manager: Task manager for handling async tasks
   :param bytes specific_ping_msg: Optional custom ping message
   :param float reconnect_interval: Reconnection interval in seconds
   :param int ping_idle_timeout: Ping timeout in seconds
   :param int ping_reply_timeout: Ping reply timeout in seconds
   :param str auto_ping_strategy: Ping strategy ("ping_when_idle" or "ping_periodically")
   :param bool enable_auto_ping: Enable automatic ping
   :param bool enable_auto_pong: Enable automatic pong response

   .. py:property:: connected
      :type: bool

      Returns True if WebSocket is connected

   .. py:method:: connect()
      :async:

      Connect to WebSocket endpoint

   .. py:method:: disconnect()

      Disconnect from WebSocket endpoint

   .. py:method:: _resubscribe()
      :async:

      Resubscribe to channels after reconnection.
      Must be implemented by subclasses.

PublicConnector
--------------

.. py:class:: PublicConnector(account_type, market: Dict[str, BaseMarket], market_id: Dict[str, str], exchange_id: ExchangeType, ws_client: WSClient, msgbus: MessageBus)

   Base class for public market data connections.

   :param AccountType account_type: Account type for the connection
   :param Dict[str,BaseMarket] market: Market information dictionary
   :param Dict[str,str] market_id: Market ID mapping dictionary  
   :param ExchangeType exchange_id: Exchange identifier
   :param WSClient ws_client: WebSocket client instance
   :param MessageBus msgbus: Message bus for publishing data

   .. py:method:: subscribe_trade(symbol: str)
      :async:

      Subscribe to trade data for a symbol.
      Must be implemented by subclasses.

   .. py:method:: subscribe_bookl1(symbol: str) 
      :async:

      Subscribe to level 1 orderbook data for a symbol.
      Must be implemented by subclasses.

   .. py:method:: subscribe_kline(symbol: str, interval: str)
      :async: 

      Subscribe to kline/candlestick data for a symbol.
      Must be implemented by subclasses.

   .. py:method:: disconnect()
      :async:

      Disconnect the WebSocket connection.

PrivateConnector
---------------

.. py:class:: PrivateConnector(account_type, market: Dict[str, BaseMarket], market_id: Dict[str, str], exchange_id: ExchangeType, ws_client: WSClient, msgbus: MessageBus, rate_limit: Optional[RateLimit] = None)

   Base class for private trading connections.

   :param AccountType account_type: Account type for the connection
   :param Dict[str,BaseMarket] market: Market information dictionary
   :param Dict[str,str] market_id: Market ID mapping dictionary
   :param ExchangeType exchange_id: Exchange identifier  
   :param WSClient ws_client: WebSocket client instance
   :param MessageBus msgbus: Message bus for publishing data
   :param Optional[RateLimit] rate_limit: Optional rate limiter configuration

   .. py:method:: create_order(symbol: str, side: OrderSide, type: OrderType, amount: Decimal, price: Decimal, time_in_force: TimeInForce, position_side: PositionSide, **kwargs) -> Order
      :async:

      Create a new order.

      :param str symbol: Trading pair symbol
      :param OrderSide side: Order side (BUY/SELL)
      :param OrderType type: Order type (MARKET/LIMIT)
      :param Decimal amount: Order quantity
      :param Decimal price: Order price (for limit orders)
      :param TimeInForce time_in_force: Time in force
      :param PositionSide position_side: Position side
      :param kwargs: Additional order parameters
      :return: Order object
      :rtype: Order

   .. py:method:: cancel_order(symbol: str, order_id: str, **kwargs) -> Order
      :async:

      Cancel an existing order.

      :param str symbol: Trading pair symbol
      :param str order_id: Order ID to cancel
      :param kwargs: Additional parameters
      :return: Updated order object
      :rtype: Order

   .. py:method:: amount_to_precision(symbol: str, amount: float, mode: Literal["round", "ceil", "floor"] = "round") -> Decimal

      Convert amount to exchange precision.

      :param str symbol: Trading pair symbol
      :param float amount: Amount to convert
      :param str mode: Rounding mode
      :return: Amount with correct precision
      :rtype: Decimal

   .. py:method:: price_to_precision(symbol: str, price: float, mode: Literal["round", "ceil", "floor"] = "round") -> Decimal

      Convert price to exchange precision.

      :param str symbol: Trading pair symbol
      :param float price: Price to convert
      :param str mode: Rounding mode
      :return: Price with correct precision
      :rtype: Decimal

Engine
------

.. py:class:: Engine(config: Config)

   Main trading engine that manages exchange connections and strategy execution.

   :param Config config: Configuration object containing strategy and connection settings

   .. py:method:: start()

      Start the trading engine.
      
      - Builds exchange connections
      - Initializes connectors
      - Starts strategy execution
      - Runs event loop until completion

   .. py:method:: dispose()

      Clean up and dispose of engine resources.
      
      - Disconnects from exchanges
      - Cancels running tasks
      - Closes event loop

OrderManagerSystem 
----------------

.. py:class:: OrderManagerSystem(cache: AsyncCache, msgbus: MessageBus, task_manager: TaskManager)

   System for managing orders and positions across exchanges.

   :param AsyncCache cache: Cache for storing order and position data
   :param MessageBus msgbus: Message bus for order events
   :param TaskManager task_manager: Task manager for async operations

   .. py:method:: add_order_msg(order: Order)

      Add an order message to the processing queue.

      :param Order order: Order object to process

   .. py:method:: add_position_msg(order: Order) 

      Add a position update message to the processing queue.

      :param Order order: Order that affects position

   .. py:method:: handle_order_event()
      :async:

      Process order events from the queue.
      
      Handles order status transitions:
      
      - PENDING -> Initial order creation
      - CANCELING -> Order cancellation in progress  
      - ACCEPTED -> Order accepted by exchange
      - PARTIALLY_FILLED -> Order partially filled
      - CANCELED -> Order canceled
      - FILLED -> Order completely filled
      - EXPIRED -> Order expired

   .. py:method:: handle_position_event()
      :async:

      Process position updates from filled/canceled orders.

   .. py:method:: start()
      :async:

      Start the order manager system.
      
      - Initializes order event handler
      - Initializes position event handler

AsyncCache
---------

.. py:class:: AsyncCache(strategy_id: str, user_id: str, task_manager: TaskManager, sync_interval: int = 60, expire_time: int = 3600)

   Cache system for storing order and position data with Redis persistence.

   :param str strategy_id: Strategy identifier
   :param str user_id: User identifier 
   :param TaskManager task_manager: Task manager for async operations
   :param int sync_interval: Interval in seconds for syncing to Redis
   :param int expire_time: Time in seconds before data expires

   .. py:method:: apply_position(order: Order)
      :async:

      Update position based on order execution.

      :param Order order: Order that affects position

   .. py:method:: get_position(symbol: str) -> Position
      :async:

      Get current position for a symbol.

      :param str symbol: Trading pair symbol
      :return: Position object if exists, else None
      :rtype: Optional[Position]

   .. py:method:: order_initialized(order: Order)

      Initialize a new order in the cache.

      :param Order order: New order to track

   .. py:method:: order_status_update(order: Order)

      Update status of existing order.

      :param Order order: Order with updated status

   .. py:method:: get_order(order_id: str) -> Order
      :async:

      Get order by ID.

      :param str order_id: Order identifier
      :return: Order object if exists, else None
      :rtype: Optional[Order]

   .. py:method:: get_symbol_orders(symbol: str, in_mem: bool = True) -> Set[str]
      :async:

      Get all order IDs for a symbol.

      :param str symbol: Trading pair symbol
      :param bool in_mem: Whether to only check in-memory cache
      :return: Set of order IDs
      :rtype: Set[str]

   .. py:method:: get_open_orders(symbol: str = None, exchange: ExchangeType = None) -> Set[str]
      :async:

      Get open order IDs filtered by symbol or exchange.

      :param Optional[str] symbol: Trading pair symbol filter
      :param Optional[ExchangeType] exchange: Exchange filter
      :return: Set of open order IDs
      :rtype: Set[str]

   .. py:method:: start()
      :async:

      Start the cache system.
      
      - Initializes Redis connection
      - Starts periodic sync task

   .. py:method:: close() 
      :async:

      Close the cache system.
      
      - Syncs final state to Redis
      - Closes Redis connection

TaskManager
----------

.. py:class:: TaskManager(loop: asyncio.AbstractEventLoop)

   Manages asynchronous tasks and handles graceful shutdown.

   :param AbstractEventLoop loop: The asyncio event loop to use

   .. py:method:: create_task(coro: asyncio.coroutines) -> asyncio.Task

      Create and track a new asyncio task.

      :param coroutine coro: Coroutine to schedule
      :return: Created task
      :rtype: asyncio.Task

   .. py:method:: wait()
      :async:

      Wait for shutdown event and handle task cleanup.

   .. py:method:: cancel()
      :async:

      Cancel all running tasks and cleanup resources.

EventSystem
----------

.. py:class:: EventSystem

   System for handling event subscriptions and notifications.

   .. py:classmethod:: on(event: str, callback: Optional[Callable] = None)

      Register an event listener. Can be used as a decorator or method.

      :param str event: Event name to listen for
      :param Optional[Callable] callback: Callback function for event
      :return: Decorator function if no callback provided
      :rtype: Callable

      Usage as decorator::

          @EventSystem.on('order_update')
          def handle_order(msg):
              pass

      Usage as method::

          EventSystem.on('order_update', handle_order)

   .. py:classmethod:: emit(event: str, *args: Any, **kwargs: Any)

      Emit an event to synchronous listeners.

      :param str event: Event name to emit
      :param args: Positional arguments to pass to listeners
      :param kwargs: Keyword arguments to pass to listeners

   .. py:classmethod:: aemit(event: str, *args: Any, **kwargs: Any)
      :async:

      Emit an event to asynchronous listeners.

      :param str event: Event name to emit
      :param args: Positional arguments to pass to listeners
      :param kwargs: Keyword arguments to pass to listeners

RedisClient
----------

.. py:class:: RedisClient

   Redis client manager for persistent storage.

   .. py:classmethod:: get_client() -> redis.Redis

      Get synchronous Redis client instance.

      :return: Redis client
      :rtype: redis.Redis

   .. py:classmethod:: get_async_client() -> redis.asyncio.Redis

      Get asynchronous Redis client instance.

      :return: Async Redis client
      :rtype: redis.asyncio.Redis

Clock
-----

.. py:class:: Clock(tick_size: float = 1.0)

   High precision clock for timing and scheduling.

   :param float tick_size: Time interval of each tick in seconds

   .. py:property:: tick_size
      :type: float

      Get the clock tick size in seconds

   .. py:property:: current_timestamp
      :type: float

      Get current timestamp in seconds

   .. py:method:: add_tick_callback(callback: Callable[[float], None])

      Register callback to be called on each tick.

      :param Callable callback: Function to call with current timestamp

   .. py:method:: run()
      :async:

      Start the clock.
      
      - Initializes tick scheduling
      - Executes callbacks on each tick
      - Maintains precise timing

SpdLog
------

.. py:class:: SpdLog

   Structured logging system with file rotation.

   .. py:classmethod:: get_logger(name: str, level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO", flush: bool = False) -> spd.Logger

      Get or create a logger instance.

      :param str name: Logger name
      :param str level: Log level
      :param bool flush: Auto-flush after each log
      :return: Logger instance
      :rtype: spdlog.Logger

   .. py:classmethod:: initialize(log_dir: str = ".logs", async_mode: bool = True, setup_error_handlers: bool = True)

      Initialize the logging system.

      :param str log_dir: Directory for log files
      :param bool async_mode: Enable async logging
      :param bool setup_error_handlers: Setup global error handlers

   .. py:classmethod:: close_all_loggers()

      Close all logger instances and release resources.

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
      :param str interval: Kline interval (e.g. "1m", "5m", "1h")

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
