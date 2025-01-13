Instruments
===========


Naming Convention
-----------------

There are two types of assets: ``SPOT`` and ``SWAP``. ``SWAP`` is divided into ``PERP`` and ``FUTURE``, and both ``PERP`` and ``FUTURE`` have ``LINEAR`` and ``INVERSE`` categories.

- SPOT: ``BTCUSDT.BINANCE`` 
- SWAP
    - PERP
        - LINEAR: ``BTCUSDT-PERP.BYBIT``
        - INVERSE: ``BTCUSD-PERP.BYBIT``
    - FUTURE
        - LINEAR: ``BTCUSDT-241227.BYBIT``
        - INVERSE: ``BTCUSD-241227.BINANCE``

.. note::

    ``SWAP`` can be either ``FUTURE`` or ``PERP``, depending on whether the character after ``-`` is ``PERP`` or a number. Eg: ``BTCUSD-241227.BINANCE`` is ``FUTURE`` while ``BTCUSDT-PERP.BYBIT`` is ``PERP``. The difference between ``LINEAR`` and ``INVERSE`` is the determination of the asset. ``LINEAR`` is determined by quote asset, while ``INVERSE`` is the price of the base asset.

Usage
-----

.. code-block:: python

    from tradebot.schema import InstrumentId

    ## create an instrument id
    instrument_id = InstrumentId.from_str("BTCUSDT-PERP.BYBIT")

    ## is_spot
    instrument_id.is_spot() # False

    ## is_swap
    instrument_id.is_linear() # True

    ## is_future
    instrument_id.is_inverse() # False


