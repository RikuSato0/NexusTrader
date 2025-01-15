Strategies
============

The core of the Tradebot user experience lies in creating and managing trading strategies. A trading strategy is defined by subclassing the ``Strategy`` class and implementing the methods necessary for the user's trading logic.

.. note::

    See the ``Strategy`` :doc:`API Reference <../api/strategy>` for a complete description of all available methods.


Strategy Implementation
--------------------------

.. code-block:: python

    from tradebot.strategy import Strategy

    class Demo(Strategy):
        def __init__(self):
            super().__init__() # <-- the super class must be called to initialize the strategy

Handlers
-----------

Handlers are methods within the Strategy class which may perform actions based on different types of events or on state changes. These methods are named with the prefix ``on_*``. You can choose to implement any or all of these handler methods depending on the specific goals and needs of your strategy.


Live Data Handlers
^^^^^^^^^^^^^^^^^^^^
These handlers receive data updates from the exchange.

.. code-block:: python

    from tradebot.schema import BookL1, Trade, Kline  


    class Demo(Strategy):

        def __init__(self):
            super().__init__()
            self.subscribe_bookl1(symbols=["BTCUSDT-PERP.OKX"])  # Subscribe to the order book for the specified symbol
            self.subscribe_trade(symbols=["BTCUSDT-PERP.OKX"])  # Subscribe to the trade data for the specified symbol
            self.subscribe_kline(symbols=["BTCUSDT-PERP.OKX"], interval="1m")  # Subscribe to the kline data for the specified symbol

        def on_bookl1(self, bookl1: BookL1):
            ...

        def on_trade(self, trade: Trade):
            ...

        def on_kline(self, kline: Kline):
            ...

Order Management Handlers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
These handlers receive order updates from the exchange.

.. code-block:: python

    from tradebot.schema import Order

    class Demo(Strategy):
        def on_pending_order(self, order: Order):
            ...

        def on_accepted_order(self, order: Order):
            ...

        def on_partially_filled_order(self, order: Order):
            ...

        def on_filled_order(self, order: Order):
            ...

        def on_canceling_order(self, order: Order):
            ...

        def on_canceled_order(self, order: Order):
            ...

        def on_failed_order(self, order: Order):
            ...

        def on_cancel_failed_order(self, order: Order):
            ...
            


Multi-Mode Support
^^^^^^^^^^^^^^^^^^^^

TradeBot supports multiple modes of operation to cater to different trading strategies and requirements. Each mode allows for flexibility in how trading logic is executed based on market conditions or specific triggers.

Event-Driven Mode
""""""""""""""""""

In this mode, trading logic is executed in response to real-time market events. The methods ``on_bookl1``, ``on_trade``, and ``on_kline`` are triggered whenever relevant data is updated, allowing for immediate reaction to market changes.

.. code-block:: python

    class Demo(Strategy):
        def __init__(self):
            super().__init__()
            self.subscribe_bookl1(symbols=["BTCUSDT-PERP.BINANCE"])

        def on_bookl1(self, bookl1: BookL1):
            # implement the trading logic Here
            pass

Timer Mode
""""""""""""""

This mode allows you to schedule trading logic to run at specific intervals. You can use the ``schedule`` method to define when your trading algorithm should execute, making it suitable for strategies that require periodic checks or actions.

.. code-block:: python

    class Demo2(Strategy):
        def __init__(self):
            super().__init__()
            self.schedule(self.algo, trigger="interval", seconds=1)

        def algo(self):
            # run every 1 second
            # implement the trading logic Here
            pass

Custom Signal Mode
""""""""""""""""""

In this mode, trading logic is executed based on custom signals. You can define your own signals and use the ``on_custom_signal`` method to trigger trading actions when these signals are received. This is particularly useful for integrating with external systems or custom event sources.

.. code-block:: python

    class Demo3(Strategy):
        def __init__(self):
            super().__init__()
            self.signal = True

        def on_custom_signal(self, signal: object):
            # implement the trading logic Here,
            # signal can be any object, it is up to you to define the signal
            pass
