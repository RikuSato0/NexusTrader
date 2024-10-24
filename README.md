# TradeBotPro

TradeBotPro is a flexible and powerful trading bot framework designed to interact with various cryptocurrency exchanges. It provides a robust architecture for managing exchange connections, order placements, and real-time data streaming via WebSockets.

## Features

- Support for multiple cryptocurrency exchanges (currently implemented: Binance, Bybit, OKX)
- Asynchronous operations using `asyncio`
- WebSocket support for real-time data streaming
- Order management (limit orders, market orders)
- Account management
- Extensible architecture for easy addition of new exchanges

## Build
To use `tradebot.ctypes`, need to build first:
```
python setup.py build_ext --inplace
```


## Installation

To install TradeBotPro, use pip:

```
pip install tradebotpro
```

## Quick Start

Here's a basic example of how to use TradeBotPro:

```python
import asyncio
from tradebot.exchange import BinanceExchangeManager, BinanceOrderManager
from tradebot.constants import CONFIG

async def main():
    config = {
        'exchange_id': 'binance',
        'sandbox': True,
        'apiKey': CONFIG['binance_future_testnet']['API_KEY'],
        'secret': CONFIG['binance_future_testnet']['SECRET'],
        'enableRateLimit': False,
    }
    
    exchange = BinanceExchangeManager(config)
    await exchange.load_markets()
    order_manager = BinanceOrderManager(exchange)
    
    res = await order_manager.place_limit_order(
        symbol='BTC/USDT:USDT',
        side='buy',
        price=59695,
        amount=0.01,
        positionSide='LONG',
    )
    
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
```

## Core Components

### ExchangeManager

The `ExchangeManager` class handles the initialization and management of exchange connections. It's responsible for loading markets and providing a unified interface for interacting with different exchanges.

### OrderManager

The `OrderManager` class manages order-related operations such as placing and canceling orders. It provides methods for creating limit and market orders, as well as canceling existing orders.

### WebsocketManager

The `WebsocketManager` class handles WebSocket connections for real-time data streaming. It provides methods for subscribing to various data streams such as order book updates, trades, and user data.

## Supported Exchanges

TradeBotPro currently supports the following exchanges:

1. Binance
2. Bybit
3. OKX

Each exchange has its own implementation of the core components, allowing for exchange-specific features and optimizations.

## Advanced Usage

### Subscribing to WebSocket Streams

Here's an example of how to subscribe to a WebSocket stream:

```python
import asyncio
from tradebot.exchange import BinanceWebsocketManager
from tradebot.constants import Url

async def callback(msg):
    print(msg)

async def main():
    ws_manager = BinanceWebsocketManager(Url.Binance.Spot)
    await ws_manager.subscribe_kline("BTCUSDT", interval='1s', callback=callback)
    
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
```

### Error Handling

TradeBotPro provides custom exceptions for better error handling. For example, the `OrderResponseError` is raised when there's an issue with an order operation:

```python
from tradebot.exceptions import OrderResponseError

try:
    res = await order_manager.place_limit_order(...)
except OrderResponseError as e:
    print(f"Error placing order: {e}")
```

## Contributing

Contributions to TradeBotPro are welcome! Please refer to our [contribution guidelines](CONTRIBUTING.md) for more information on how to get started.

## License

TradeBotPro is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
