Usage
=====

Basic Usage
-----------

.. code-block:: python

   from tradebot.exchange.binance import BinanceExchangeManager

   # Initialize exchange manager
   config = {
       "apiKey": "your_api_key",
       "secret": "your_secret_key"
   }
   exchange = BinanceExchangeManager(config)
   exchange.load_markets()

Advanced Configuration
----------------------

Configuration can be done via configuration files or environment variables.

Supported Exchanges
-------------------

- Binance
- OKX
- Bybit 
