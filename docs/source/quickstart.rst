Quick Start Guide
=================

1. Starting with a Simple TWAP Strategy
------------------------------------------

Configuring ExchangeManager
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Each exchange has its own ``ExchangeManager``, imported from ``tradebot.exchange.{$exchange_name}``. Using Bybit as an example:

.. code-block:: python

    from tradebot.exchange.bybit import ExchangeManager

    config = {
        "apiKey": BYBIT_API_KEY,
        "secret": BYBIT_API_SECRET,
        "sandbox": True,
    }

    exchange = BybitExchangeManager(config)

API key and secret can be configured by copying ``config_demo.cfg`` to ``config.cfg`` in the ``.keys`` folder:

.. code-block:: ini

    [bybit]
    API_KEY = your_api_key
    SECRET = your_api_secret

Then you can import related configurations using ``CONFIG``:

.. code-block:: python

    from tradebot.constants import CONFIG

    BYBIT_API_KEY = CONFIG["bybit_testnet_2"]["API_KEY"]
    BYBIT_API_SECRET = CONFIG["bybit_testnet_2"]["SECRET"]

Public Market Data
^^^^^^^^^^^^^^^^^^

Public market data supports ``Trade``, ``BookL1/L2``, ``Kline``, ``MarkPrice``, ``IndexPrice``, and ``FundingRate``. These are imported from ``tradebot.types``.

BookL1 Data Structure
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    class BookL1(Struct, gc=False):
        exchange: str
        symbol: str
        bid: float
        ask: float
        bid_size: float
        ask_size: float
        timestamp: int

BookL2 Data Structure
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    class BookL2(Struct):
        exchange: str
        symbol: str
        bids: List[Tuple[float, float]]
        asks: List[Tuple[float, float]]
        timestamp: int

Trade Data Structure
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    class Trade(Struct, gc=False):
        exchange: str
        symbol: str
        price: float
        size: float
        timestamp: int

Kline Data Structure
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    class Kline(Struct, gc=False):
        exchange: str
        symbol: str
        interval: str
        open: float
        high: float
        low: float
        close: float
        volume: float
        timestamp: int

Mark Price Data Structure
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    class MarkPrice(Struct, gc=False):
        exchange: str
        symbol: str
        price: float
        timestamp: int

Funding Rate Data Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    class FundingRate(Struct, gc=False):
        exchange: str
        symbol: str
        rate: float
        timestamp: int
        next_funding_time: int

Index Price Data Structure
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    class IndexPrice(Struct, gc=False):
        exchange: str
        symbol: str
        price: float
        timestamp: int

Retrieving Market Data
^^^^^^^^^^^^^^^^^^^^^^

Market data is retrieved using ``PublicConnector``. Each exchange has its own ``PublicConnector``, which can be imported from ``tradebot.exchange.{$exchange_name}``. Example:

.. code-block:: python

    from tradebot.strategy import Strategy
    from tradebot.exchange.bybit import BybitPublicConnector, BybitAccountType

    class Demo(Strategy):
        # Strategy logic...

    conn_linear = BybitPublicConnector(BybitAccountType.LINEAR_TESTNET, exchange)
    demo.add_public_connector(conn_linear)

    await demo.subscribe_bookl1(BybitAccountType.LINEAR_TESTNET, "ETH/USDT:USDT")

Since exchanges have multiple ``AccountType``\s, you need to specify the ``AccountType`` when subscribing and pass the ``ExchangeManager``. Add the connector to the ``Strategy`` using ``add_public_connector``. As a ``Strategy`` can have multiple ``PublicConnector``\s, specify the ``AccountType`` when subscribing:

.. code-block:: python

    await demo.subscribe_bookl1(BybitAccountType.LINEAR_TESTNET, "ETH/USDT:USDT")

Private Connector
^^^^^^^^^^^^^^^^^

``PrivateConnector`` handles ``Order`` callbacks and ``Position`` management, distinguishing between accounts and strategies:

.. code-block:: python

    from tradebot.exchange.bybit import PrivateConnector

    # Existing code...

    private_conn = BybitPrivateConnector(
        exchange,
        account_type=BybitAccountType.ALL_TESTNET,
        strategy_id="strategy_vwap",
        user_id="test_user",
    )

Strategy
^^^^^^^^^

All strategy implementations must inherit from ``Strategy``, which provides the following methods:

Adding Connectors
~~~~~~~~~~~~~~~~~~

- ``add_public_connector``
- ``add_private_connector``

Market Data Subscription
~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``subscribe_bookl1``
- ``subscribe_trade``
- ``subscribe_kline``
- ``subscribe_markprice``
- ``subscribe_fundingrate``
- ``subscribe_indexprice``

Order Callbacks
~~~~~~~~~~~~~~~~

- ``on_accepted_order``
- ``on_partially_filled_order``
- ``on_filled_order``
- ``on_canceled_order``

Market Data Retrieval
~~~~~~~~~~~~~~~~~~~~~~

- ``get_bookl1``
- ``get_trade``
- ``get_kline``
- ``get_markprice``
- ``get_fundingrate``
- ``get_indexprice``

Market Data Callbacks
~~~~~~~~~~~~~~~~~~~~~~

- ``on_trade``
- ``on_bookl1``
- ``on_kline``
- ``on_markprice``
- ``on_fundingrate``
- ``on_indexprice``

Order Management
~~~~~~~~~~~~~~~~~~

- ``create_order``
- ``cancel_order``

Precision Formatting
^^^^^^^^^^^^^^^^^^^^^^^

- ``amount_to_precision``
- ``price_to_precision``

Event Loop
^^^^^^^^^^^^^^^


- ``on_tick`` - Executes at fixed intervals
- ``run`` - Starts the strategy

Cache/Market Access
^^^^^^^^^^^^^^^^^^^^

- ``cache`` - Access the ``PrivateConnector``'s Cache
- ``market`` - Access the ``PrivateConnector``'s Market

Cache
^^^^^

``Cache`` is the ``PrivateConnector``'s storage for ``Orders`` and ``Positions``. It provides the following public methods:

- ``get_order`` - Retrieve an Order by OrderID
- ``get_symbol_orders`` - Get all Orders for a Symbol
- ``get_open_orders`` - Get all Open Orders for a Symbol
- ``get_position`` - Get Position for a Symbol

Putting it All Together
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Here's a simple TWAP strategy example:

.. code-block:: python

    import asyncio
    from tradebot.constants import CONFIG
    from tradebot.types import Order
    from tradebot.constants import OrderSide, OrderType, OrderStatus
    from tradebot.strategy import Strategy
    from decimal import Decimal
    from tradebot.exchange.bybit import (
        BybitPublicConnector,
        BybitPrivateConnector,
        BybitAccountType,
        BybitExchangeManager,
    )

    BYBIT_API_KEY = CONFIG["bybit_testnet_2"]["API_KEY"]
    BYBIT_API_SECRET = CONFIG["bybit_testnet_2"]["SECRET"]


    class Demo(Strategy):
        def __init__(self):
            super().__init__(tick_size=1)

            self.amount = Decimal(5)
            self.symbol = "ETH/USDT:USDT"
            self.pos = Decimal(0)
            self.order_id = None
            self.finished = False

        async def on_tick(self, tick):
            if self.finished:
                return
            if self.order_id:
                order: Order = self.cache(BybitAccountType.ALL_TESTNET).get_order(
                    self.order_id
                ) # 获取`Order`
                print(order)
                if order.status == OrderStatus.FILLED:
                    if self.pos < self.amount:
                        self.pos += order.filled
                        print(f"Filled {self.pos} of {self.amount}")
                    else:
                        print("TWAP completed")
                        self.finished = True
                else:
                    order_cancel = await self.cancel_order(
                        account_type=BybitAccountType.ALL_TESTNET,
                        symbol=self.symbol,
                        order_id=self.order_id,
                    )
                    if not order_cancel.success:
                        print(f"Failed to cancel order {self.order_id}")
                        order: Order = self.cache(BybitAccountType.ALL_TESTNET).get_order(
                            self.order_id
                        )
                        self.pos += order.amount
                    else:
                        print(f"Canceled order {self.order_id}")
                        self.order_id = None

            book = self.get_bookl1("bybit", self.symbol)

            size = max(
                self.market(BybitAccountType.ALL_TESTNET)[self.symbol].limits.amount.min,
                min(book.ask_size, self.amount - self.pos),
            )
            amount = self.amount_to_precision(
                account_type=BybitAccountType.ALL_TESTNET,
                symbol=self.symbol,
                amount=size,
            )

            price = self.price_to_precision(
                account_type=BybitAccountType.ALL_TESTNET,
                symbol=self.symbol,
                price=book.ask,
            )

            if self.pos < self.amount:
                open_orders = self.cache(BybitAccountType.ALL_TESTNET).get_open_orders(self.symbol)
                if self.order_id in open_orders and self.order_id:
                    print(f"Symbol {self.symbol} still have open orders: {self.order_id}")
                    return
                order = await self.create_order(
                    account_type=BybitAccountType.ALL_TESTNET,
                    symbol=self.symbol,
                    side=OrderSide.BUY,
                    type=OrderType.LIMIT,
                    amount=amount,
                    price=price,
                )
                self.order_id = order.id
                print(f"Created order {order}")


    async def main():
        try:
            config = {
                "apiKey": BYBIT_API_KEY,
                "secret": BYBIT_API_SECRET,
                "sandbox": True,
            }

            exchange = BybitExchangeManager(config)

            conn_linear = BybitPublicConnector(BybitAccountType.LINEAR_TESTNET, exchange)

            private_conn = BybitPrivateConnector(
                exchange,
                account_type=BybitAccountType.ALL_TESTNET,
                strategy_id="strategy_vwap",
                user_id="test_user",
            )

            demo = Demo()
            demo.add_public_connector(conn_linear)
            demo.add_private_connector(private_conn)
            await demo.subscribe_bookl1(BybitAccountType.LINEAR_TESTNET, "ETH/USDT:USDT")
            await demo.run()

        except asyncio.CancelledError:
            print("Cancelled")
        finally:
            await conn_linear.disconnect()


    if __name__ == "__main__":
        asyncio.run(main())

This example demonstrates a basic Time-Weighted Average Price (TWAP) strategy using the tradebot framework.


