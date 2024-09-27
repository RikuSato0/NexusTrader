# TradeBotPro

TradeBotPro is a flexible and powerful trading bot framework designed to interact with various cryptocurrency exchanges. It provides a robust architecture for managing exchange connections, order placements, and real-time data streaming via WebSockets.

## Features

- Support for multiple cryptocurrency exchanges (currently implemented: Binance, Bybit, OKX)
- Asynchronous operations using `asyncio`
- WebSocket support for real-time data streaming
- Order management (limit orders, market orders)
- Account management
- Extensible architecture for easy addition of new exchanges

## Project Structure

The project is organized into several key components:

1. `ExchangeManager`: Handles the initialization and management of exchange connections.
2. `OrderManager`: Manages order-related operations such as placing and canceling orders.
3. `AccountManager`: Manages account-related operations.
4. `WebsocketManager`: Handles WebSocket connections for real-time data streaming.

## Installation

(Add installation instructions here)

## Usage

Here's a basic example of how to use TradeBotPro:

```python
import asyncio
from tradebot.exchange import BinanceExchangeManager, BinanceOrderManager

async def main():
    config = {
        "exchange_id": "binance",
        "apiKey": "your_api_key",
        "secret": "your_secret_key",
        "enableRateLimit": True,
        "sandbox": True  # Use sandbox mode for testing
    }

    exchange = BinanceExchangeManager(config)
    order_manager = BinanceOrderManager(exchange)

    await exchange.load_markets()

    # Place a limit order
    order = await order_manager.place_limit_order(
        symbol="BTC/USDT",
        side="buy",
        amount=0.001,
        price=30000
    )

    print(f"Order placed: {order}")

    await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Supported Exchanges

- Binance
- Bybit
- OKX

## WebSocket Subscriptions

TradeBotPro supports various WebSocket subscriptions for real-time data:

- Order book updates
- Trades
- User account updates
- Position updates
- Order updates
- Market data (e.g., klines)

Each exchange implementation provides specific methods for subscribing to these data streams.


## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.# TradeBotPro
