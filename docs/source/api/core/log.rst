Logging Module
=============

.. automodule:: tradebot.core.log
   :members:
   :undoc-members:
   :show-inheritance:

Overview
--------

The logging module provides structured logging functionality for the trading bot.
It includes formatters and handlers for both console and file logging.

Key Components
-------------

- setup_logging: Function to initialize logging configuration
- LogFormatter: Custom formatter for structured log output
- LogHandler: Custom handler for log routing

Usage Example
------------

.. code-block:: python

   from tradebot.core.log import setup_logging
   
   # Initialize logging
   setup_logging(
       log_level="INFO",
       log_file="trading.log"
   )
   
   # Use logger
   logger = logging.getLogger(__name__)
   logger.info("Trading started", extra={
       "exchange": "binance",
       "symbol": "BTCUSDT"
   }) 
