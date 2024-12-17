import asyncio
import time
import ccxt
from typing import Dict
from collections import defaultdict

from tradebot.constants import OrderSide, OrderType
from tradebot.core import Strategy
from tradebot.types import Order, BookL1

from tradebot.constants import CONFIG
from tradebot.exchange.bybit import (
    BybitPublicConnector,
    BybitPrivateConnector,
    BybitAccountType,
    BybitExchangeManager,
)


class PureMarketMakingStrategy(Strategy):
    def __init__(
        self,
        api: ccxt.bybit = None,
        # Market making parameters
        bid_spread: float = 0.01,  # 1% spread
        ask_spread: float = 0.01,  # 1% spread
        order_amount: float = 0.1,  # Base order size
        min_spread: float = 0.002,  # Minimum spread to maintain
        order_refresh_time: float = 30.0,  # Order refresh time in seconds
        max_order_age: float = 1800.0,  # Maximum order age in seconds
        # Risk parameters
        inventory_skew_enabled: bool = True,
        target_base_pct: float = 0.5,  # Target base asset percentage
        max_deviation: float = 0.05,  # Maximum deviation from target
    ):
        super().__init__(tick_size=1)

        # Strategy parameters
        self.bid_spread = bid_spread
        self.ask_spread = ask_spread
        self.order_amount = order_amount
        self.min_spread = min_spread
        self.order_refresh_time = order_refresh_time
        self.max_order_age = max_order_age

        # Risk management parameters
        self.inventory_skew_enabled = inventory_skew_enabled
        self.target_base_pct = target_base_pct
        self.max_deviation = max_deviation

        # Internal state
        self._active_orders: Dict[str, Dict[str, Order]] = defaultdict(dict)
        self._last_order_refresh: Dict[str, float] = defaultdict(float)
        self._in_flight_orders: Dict[str, bool] = defaultdict(bool)

        # Tasks management
        self.active_tasks = set()
        self.is_running = True
        self.api = api

    async def create_orders(self, symbol: str):
        """Create bid and ask orders for market making"""
        if self._in_flight_orders[symbol]:
            return

        self._in_flight_orders[symbol] = True
        try:
            # Get current market prices
            book = self.get_bookl1("bybit", symbol)
            # mid_price = Decimal(str(book.bid + book.ask)) / Decimal("2")
            mid_price = (book.bid + book.ask) / 2

            # Calculate order prices with spreads
            bid_price = mid_price * (1 - self.bid_spread)
            ask_price = mid_price * (1 + self.ask_spread)

            # Apply inventory skew if enabled

            """
            期望：目标是保持50%的BTC和50%的USDT
            当前状态：
                - 持有60% BTC，40% USDT
                - inventory_ratio = 0.6
                - target_base_pct = 0.5

                计算调整：
                bid_adjustment = (0.6 - 0.5) * 0.05 = 0.005 (0.5%)
                ask_adjustment = (0.5 - 0.6) * 0.05 = -0.005 (-0.5%)

                如果市场中间价是 $50,000：
                - 买入价会降低：$50,000 * (1 - 0.005) = $49,750
                - 卖出价会降低：$50,000 * (1 + (-0.005)) = $49,750

            当前状态：
                - 持有40% BTC，60% USDT
                - inventory_ratio = 0.4
                - target_base_pct = 0.5

                计算调整：
                bid_adjustment = (0.4 - 0.5) * 0.05 = -0.005 (-0.5%)
                ask_adjustment = (0.5 - 0.4) * 0.05 = 0.005 (0.5%)

                如果市场中间价是 $50,000：
                - 买入价会提高：$50,000 * (1 - (-0.005)) = $50,250
                - 卖出价会提高：$50,000 * (1 + 0.005) = $50,250
            """

            if self.inventory_skew_enabled:
                inventory_ratio = self.get_inventory_ratio(symbol)
                bid_adjustment = (
                    inventory_ratio - self.target_base_pct
                ) * self.max_deviation
                ask_adjustment = (
                    self.target_base_pct - inventory_ratio
                ) * self.max_deviation

                bid_price *= 1 - bid_adjustment
                ask_price *= 1 + ask_adjustment

            # Ensure minimum spread
            if (ask_price - bid_price) / mid_price < self.min_spread:
                return

            # Create orders
            bid_order = await self.create_order(
                account_type=BybitAccountType.ALL_TESTNET,
                symbol=symbol,
                side=OrderSide.BUY,
                type=OrderType.LIMIT,
                amount=self.order_amount,
                price=self.price_to_precision(
                    account_type=BybitAccountType.ALL_TESTNET,
                    symbol=symbol,
                    price=bid_price,
                ),
            )

            ask_order = await self.create_order(
                account_type=BybitAccountType.ALL_TESTNET,
                symbol=symbol,
                side=OrderSide.SELL,
                type=OrderType.LIMIT,
                amount=self.order_amount,
                price=self.price_to_precision(
                    account_type=BybitAccountType.ALL_TESTNET,
                    symbol=symbol,
                    price=ask_price,
                ),
            )

            if bid_order.id:
                self._active_orders[symbol][bid_order.id] = bid_order
            if ask_order.id:
                self._active_orders[symbol][ask_order.id] = ask_order

            self._last_order_refresh[symbol] = time.time()

        finally:
            self._in_flight_orders[symbol] = False

    async def cancel_old_orders(self, symbol: str):
        """Cancel orders that have been active for too long"""
        current_timestamp = time.time()
        orders_to_cancel = []

        for order_id, order in self._active_orders[symbol].items():
            if (current_timestamp - order.timestamp / 1000) > self.max_order_age:
                orders_to_cancel.append(order_id)

        for order_id in orders_to_cancel:
            await self.cancel_order(
                account_type=BybitAccountType.ALL_TESTNET,
                symbol=symbol,
                order_id=order_id,
            )
            del self._active_orders[symbol][order_id]

    def get_inventory_ratio(self, symbol: str) -> float:
        """Calculate the current inventory ratio"""
        position = self.fetch_positions().get(symbol, 0)
        total_position = abs(position)
        if total_position == 0:
            return float(self.target_base_pct)
        return float(position / total_position)

    def fetch_positions(self):
        # todo: 
        pos = self.api.fetch_positions()
        return {
            p["symbol"]: (-1 if p["side"] == "short" else 1)
            * p["contracts"]
            * p["contractSize"]
            for p in pos
        }

    async def maintain_market_making(self, symbol: str):
        """Main market making loop for a symbol"""
        while self.is_running:
            try:
                current_time = time.time()

                # Cancel old orders
                await self.cancel_old_orders(symbol)

                # Check if it's time to refresh orders
                if (
                    current_time - self._last_order_refresh[symbol]
                ) > self.order_refresh_time:
                    # Cancel all active orders
                    for order_id in list(self._active_orders[symbol].keys()):
                        await self.cancel_order(
                            account_type=BybitAccountType.ALL_TESTNET,
                            symbol=symbol,
                            order_id=order_id,
                        )
                    self._active_orders[symbol].clear()

                    # Create new orders
                    await self.create_orders(symbol)

                await asyncio.sleep(1)

            except Exception as e:
                self.log.error(f"Error in market making loop for {symbol}: {str(e)}")
                await asyncio.sleep(5)

    def on_bookl1(self, bookl1: BookL1):
        """Handle order book updates"""
        symbol = bookl1.symbol
        if not self._in_flight_orders[symbol]:
            task = asyncio.create_task(self.create_orders(symbol))
            self.active_tasks.add(task)
            task.add_done_callback(self.active_tasks.discard)

    async def start_market_making(self, symbols: list[str]):
        """Start market making for multiple symbols"""
        tasks = []
        for symbol in symbols:
            task = asyncio.create_task(self.maintain_market_making(symbol))
            tasks.append(task)
            self.active_tasks.add(task)
            task.add_done_callback(self.active_tasks.discard)

        await asyncio.gather(*tasks)

    async def shutdown(self):
        """Gracefully shutdown the strategy"""
        self.is_running = False
        self.log.info("Stopping strategy, cancelling all orders...")

        # Cancel all active orders
        for symbol in self._active_orders:
            for order_id in list(self._active_orders[symbol].keys()):
                await self.cancel_order(
                    account_type=BybitAccountType.ALL_TESTNET,
                    symbol=symbol,
                    order_id=order_id,
                )

        # Wait for all tasks to complete
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks)
        self.log.info("Strategy shutdown complete")


async def main():
    try:
        # Initialize exchange and configuration
        config = {
            "apiKey": CONFIG["bybit"]["API_KEY"],
            "secret": CONFIG["bybit"]["SECRET"],
            "sandbox": True,  # Set to False for production
        }

        # Create exchange manager
        exchange = BybitExchangeManager(config)

        # Initialize connectors
        conn_linear = BybitPublicConnector(BybitAccountType.SPOT, exchange)

        private_conn = BybitPrivateConnector(
            exchange,
            account_type=BybitAccountType.ALL_TESTNET,
            strategy_id="strategy_pmm",
            user_id="pmm_user",
            rate_limit=20,
        )

        # Initialize strategy with desired parameters
        pmm = PureMarketMakingStrategy(
            api=exchange.api,
            bid_spread=0.001,  # 0.1% spread
            ask_spread=0.001,  # 0.1% spread
            order_amount=0.01,  # Base order size
            min_spread=0.0005,  # Minimum spread
            order_refresh_time=30.0,  # Refresh orders every 30 seconds
            max_order_age=1800.0,  # Maximum order age of 30 minutes
            inventory_skew_enabled=True,
            target_base_pct=0.5,  # Target 50% inventory
            max_deviation=0.05,  # 5% maximum deviation
        )

        # Add connectors to strategy
        pmm.add_public_connector(conn_linear)
        pmm.add_private_connector(private_conn)

        # Subscribe to market data for desired trading pairs
        symbols = ["BTCUSDT"]  # Add your desired trading pairs
        for symbol in symbols:
            await pmm.subscribe_bookl1(BybitAccountType.SPOT, symbol)

        # Wait for market data to be ready
        await pmm.wait_for_market_data()

        # Start market making
        await pmm.start_market_making(symbols)

    except asyncio.CancelledError:
        print("Strategy execution cancelled")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        # Ensure proper shutdown
        await pmm.shutdown()
        await conn_linear.disconnect()
        await private_conn.disconnect()


# async def main():
#     config = {
#         "apiKey": CONFIG["bybit"]["API_KEY"],
#         "secret": CONFIG["bybit"]["SECRET"],
#         "sandbox": True,  # Set to False for production
#     }
#     exchange = BybitExchangeManager(config)
#     print(exchange.api.fetch_position("BTCUSDT"))


if __name__ == "__main__":
    asyncio.run(main())
