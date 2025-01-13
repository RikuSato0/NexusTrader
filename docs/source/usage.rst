Usage
=====

Basic Usage
-----------

.. note::
   This is a note used to highlight important information.

.. warning::
   This is a warning to alert users about potential issues.

.. tip::
   This is a tip providing helpful suggestions.

.. important::
   This is important information emphasizing key points.

.. todo::
   This is a todo item marking work that needs to be completed.

.. danger::
   This is a danger notice warning about operations with serious consequences.

.. hint::
   This is a hint providing suggestive information.

Code Example
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

.. caution::
   Always keep your API keys secure and never commit them to version control.

Advanced Configuration
----------------------

Configuration can be done via configuration files or environment variables.

Supported Exchanges
-------------------

- Binance
- OKX
- Bybit 

.. note::
   This feature supports the following:
   
   - Feature 1
   - Feature 2
   
   .. code-block:: python
   
      print("You can even include code blocks in admonitions")

.. important::
   **Advanced Configuration**

   When setting up the trading bot:
   
   1. Configure your API keys
   2. Set risk parameters
   3. Test in sandbox mode first
   
   .. code-block:: python
   
      config = {
          "risk_level": "conservative",
          "max_position_size": 0.1
      }
