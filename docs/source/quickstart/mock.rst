Set up mock trading
======================

NexusTrader provides a mock trading environment to test your trading strategies without risking any real money. In this section, we will show you how to set up mock trading.

Mock Trading Account
---------------------

Though in the real trading environment, you need to set up a real trading account for the exchanges, in the mock trading environment, you can use the mock trading account provided by the NexusTrader. There are 
only three types of mock trading accounts:

- SPOT_MOCK
- LINEAR_MOCK
- INVERSE_MOCK

For each exchange, just set the ``account_type`` to the corresponding mock trading account type.

.. code-block:: python

    from nexustrader.config import Config
    from nexustrader.exchange.binance import BinanceAccountType

    config = Config(
         strategy_id="strategy_mock",
         user_id="user_test",
         strategy=Demo(),
         basic_config={
             ExchangeType.BINANCE: BasicConfig(
                 api_key=BINANCE_API_KEY,
                 secret=BINANCE_SECRET,
                 testnet=False,
             )
         },
         public_conn_config={
             ExchangeType.BINANCE: [
                 PublicConnectorConfig(
                     account_type=BinanceAccountType.USD_M_FUTURE,
                     rate_limit=RateLimit(
                         max_rate=20,
                         time_period=1,
                     ),
                 )
             ]
         },
         private_conn_config={
             ExchangeType.BINANCE: [
                 MockConnectorConfig(
                     initial_balance={"USDT": 100000}, # setup the initial balance
                     account_type=BinanceAccountType.LINEAR_MOCK, # setup the mock trading account type
                     fee_rate=0.0005, # setup the fee rate
                     quote_currency="USDT", # setup the quote currency, this if for pnl calculation
                     overwrite_balance=False, # overwrite the balance
                     overwrite_position=False, # overwrite the position
                     update_interval=60, # setup the update interval for sync balance and position
                     leverage=1, # setup the leverage
                 )
             ]
         },
         db_path="/data/grafana-data/cache.db", # The ``db_path`` is the path to the database file
     )

.. note::

    For now, the mock trading account is only available for the Mock Perpetual Futures.

Supported Order Types
-----------------------

In the mock trading environment, you can only use the ``MARKET`` order type, which means the mocking price is best `bid` for buy order and best `ask` for sell order. The order will be immediately filled.

There are several checks before you place an order:

- Check the balance and position
- Check the leverage
- Check the symbol availability 


.. note::

    The mock trading is not the same as testnet, the mock trading is a real trading environment, but the price is mocked.
