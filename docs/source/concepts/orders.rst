Orders
========

This guide offers detailed information about the various order types available on the platform, as well as the execution instructions supported for each.

Orders are a fundamental component of any algorithmic trading strategy. Tradebot has integrated a wide range of order types and execution instructions, from standard to advanced, to maximize the potential functionality of trading venues. This allows traders to set specific conditions and instructions for order execution and management, enabling the creation of virtually any type of trading strategy.


Overview
-----------

There are two types of orders: ``Basic Order`` and ``Algorithmic Order``. 

- ``Basic Order``
    - ``Limit Order`` 
    - ``Market Order``
- ``Algorithmic Order``
    - ``TWAP``

You can create a ``Basic Order`` by calling the ``create_order`` method in ``Strategy`` class. 

.. code-block:: python

    from tradebot.strategy import Strategy
    from tradebot.constants import ExchangeType, OrderSide, OrderType

    class Demo(Strategy):
        def __init__(self):
            super().__init__()
            self.create_order(
                order_type=OrderType.LIMIT, 
                symbol="BTCUSDT", 
                side=OrderSide.BUY, 
                price=10000,
                amount=1,
            )

You can create an ``Algorithmic Order`` by calling the ``create_twap`` method in ``Strategy`` class.

.. code-block:: python

    self.create_twap(
        symbol=symbol,
        side=OrderSide.BUY if diff > 0 else OrderSide.SELL,
        amount=abs(diff),
        duration=65,
        wait=5,
        account_type=BybitAccountType.UNIFIED_TESTNET, # recommend to specify the account type
    )

Order Status
---------------


