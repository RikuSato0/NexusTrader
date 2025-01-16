nexustrader.config
====================

.. currentmodule:: nexustrader.config

Configuration Classes
-------------------------

Config
~~~~~~

.. autoclass:: Config
    :members:
    :undoc-members:
    :show-inheritance:

    Main configuration class that holds all settings for the trading system.

    **Key Parameters:**

    - strategy_id: Unique identifier for the strategy
    - user_id: User identifier
    - strategy: Strategy instance
    - basic_config: Exchange basic configurations
    - public_conn_config: Public connector configurations
    - private_conn_config: Private connector configurations
    - zero_mq_signal_config: Optional ZeroMQ signal configuration
    - cache_sync_interval: Cache synchronization interval in seconds
    - cache_expire_time: Cache expiration time in seconds

Component Configs
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: BasicConfig
    :members:
    :undoc-members:
    :show-inheritance:

    Basic configuration for exchange connections.

    **Parameters:**

    - api_key: API key for the exchange
    - secret: Secret key for the exchange
    - testnet: Whether to use testnet
    - passphrase: Optional passphrase (required for some exchanges)

.. autoclass:: PublicConnectorConfig
    :members:
    :undoc-members:
    :show-inheritance:

    Configuration for public market data connections.

    **Parameters:**

    - account_type: Type of account for the connection

.. autoclass:: PrivateConnectorConfig
    :members:
    :undoc-members:
    :show-inheritance:

    Configuration for private trading connections.

    **Parameters:**

    - account_type: Type of account for the connection
    - rate_limit: Optional rate limiting configuration

.. autoclass:: ZeroMQSignalConfig
    :members:
    :undoc-members:
    :show-inheritance:
    :no-index:
