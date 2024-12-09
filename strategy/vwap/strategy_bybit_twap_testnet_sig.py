import asyncio
import pickle
import time
import os
import ccxt
import math
import collections
import zmq.asyncio
import orjson
from typing import Dict, Tuple
from collections import defaultdict
from tradebot.constants import CONFIG
from tradebot.types import Order, BookL1
from tradebot.constants import OrderSide, OrderType, OrderStatus
from tradebot.strategy import Strategy
from tradebot.exchange.bybit.types import BybitMarket
from decimal import Decimal
from tradebot.entity import EventSystem
from tradebot.exchange.bybit import (
    BybitPublicConnector,
    BybitPrivateConnector,
    BybitAccountType,
    BybitExchangeManager,
)

DIR_PATH = os.path.dirname(os.path.abspath(__file__))

BYBIT_API_KEY = CONFIG["bybit_testnet_2"]["API_KEY"]
BYBIT_API_SECRET = CONFIG["bybit_testnet_2"]["SECRET"]


class BybitSignal:
    def __init__(self, market: Dict[str, BybitMarket] = None):
        context = zmq.asyncio.Context()
        self.socket = context.socket(zmq.SUB)
        self.socket.connect("ipc:///tmp/zmq_data_test")
        self.socket.setsockopt(zmq.SUBSCRIBE, b"")
        self.market = market
        self.mutiplier = Decimal(str(0.5))
        self.valid_symbols = market.keys()
        self.strategy = None
        self.first_subscribed = True

    def set_strategy(self, strategy: Strategy):
        self.strategy = strategy

    async def receive(self):
        while True:
            pos = {}
            response = await self.socket.recv()
            data = orjson.loads(response)

            for d in data:
                symbol: str = d["instrumentID"]
                symbol = symbol.replace("USDT.BBP", "/USDT:USDT")

                if symbol in self.valid_symbols:
                    if self.first_subscribed:
                        await self.strategy.subscribe_bookl1(
                            BybitAccountType.LINEAR_TESTNET, symbol
                        )
                    pos[symbol] = (
                        Decimal(str(d["position"]))
                        * Decimal(str(self.market[symbol].precision.amount))
                        * self.mutiplier
                    )
            if self.first_subscribed:
                self.first_subscribed = False
                await self.strategy.wait_for_market_data()
                await self.strategy.run()

            if self.strategy.ready:
                await EventSystem.aemit("signal", pos)


class RollingDiffSum:
    def __init__(self, n):
        self.n = n
        self.prev_price = None
        self.curr_price = None
        self.diffs = collections.deque(maxlen=n)

    def input(self, price):
        if self.curr_price is not None:
            diff = price - self.curr_price
            self.diffs.append(diff)

        self.prev_price = self.curr_price
        self.curr_price = price

        if len(self.diffs) == self.n:
            rolling_sum = sum(self.diffs)
            return rolling_sum
        else:
            return 0


rolling_diff_sum = RollingDiffSum(20)


class VwapStrategy(Strategy):
    def __init__(self, api: ccxt.bybit = None):
        super().__init__(tick_size=1)
        self.current_positions = self._load_positions()
        self.trending_signal = defaultdict(int)
        self._in_ordering = defaultdict(bool)  # default to False

        self.active_tasks = set()
        self.is_running = True
        self.api = api

        EventSystem.on("signal", self.on_signal)

    def fetch_positions(self):
        pos = self.api.fetch_positions()
        return {
            p["symbol"]: (-1 if p["side"] == "short" else 1)
            * p["contracts"]
            * p["contractSize"]
            for p in pos
        }

    def _load_positions(self):
        try:
            with open(
                os.path.join(DIR_PATH, "positions.pkl"), "rb"
            ) as f:  # Changed extension and mode
                return pickle.load(f)
        except FileNotFoundError:
            return defaultdict(Decimal)

    def _save_positions(self, positions):
        with open(
            os.path.join(DIR_PATH, "positions.pkl"), "wb"
        ) as f:  # Changed extension and mode
            pickle.dump(positions, f)

    def _get_order_params(
        self, symbol: str, pos: Decimal
    ) -> Tuple[OrderSide, Decimal, bool]:
        """
        current_positions: Dict[str, float]
        positions: Dict[str, float]


        1. positions - current_positions > 0
            - positions > 0, current_positions = 0 -> side = BUY, reduce_only = False (0 -> 10)
            - positions > 0, current_postions > 0 -> side = BUY, reduce_only = False (5 -> 20)

            - positions > 0, current_positions < 0 -> side = BUY, reduce_only = True -> side = BUY, reduce_only=False (-5 -> 0) (0 -> 10)

            - positions = 0, current_positions < 0 -> side = BUY, reduce_only = True (-10 -> 0)
            - positions < 0, current_positions < 0 -> side = BUY, reduce_only = True (-10 -> -5)


        2. positions - current_positions < 0
            - positions > 0, current_positions > 0 -> side = SELL, reduce_only = True
            - positions = 0, current_positions > 0 -> side = SELL, reduce_only = True

            - positions < 0, current_positions = 0 -> side = SELL, reduce_only = False
            - positions < 0, current_positions < 0 -> side = SELL, reduce_only = False
            - positions < 0, current_positions > 0 -> side = SELL, reduce_only = True -> side = SELL, reduce_only=False
        """
        current_pos = self.current_positions[symbol]
        if pos - current_pos > 0:
            side = OrderSide.BUY
            if pos > 0 and current_pos >= 0:
                reduce_only = False
            elif pos <= 0 and current_pos < 0:
                reduce_only = True
            else:
                pos = Decimal(str(0))
                reduce_only = True
            amount = pos - current_pos
            return side, amount, reduce_only
        elif pos - current_pos < 0:
            side = OrderSide.SELL
            if pos < 0 and current_pos <= 0:
                reduce_only = False
            elif pos >= 0 and current_pos > 0:
                reduce_only = True
            else:
                pos = Decimal(str(0))
                reduce_only = False
            amount = current_pos - pos
            return side, amount, reduce_only

    async def on_signal(self, positions: Dict[str, Dict]):
        if not self.is_running:
            return

        for symbol, pos in positions.items():
            res = self._get_order_params(symbol, pos)
            if res:
                side, amount, reduce_only = res
                if not self._in_ordering[symbol] and amount >= max(
                    6
                    / (
                        self.get_bookl1("bybit", symbol).ask
                        + self.get_bookl1("bybit", symbol).bid
                    )
                    / 2,
                    self.market(BybitAccountType.ALL_TESTNET)[symbol].limits.amount.min,
                ):
                    task = asyncio.create_task(
                        self.vwap_order(symbol, side, amount, reduce_only)
                    )
                    self.active_tasks.add(task)
                    task.add_done_callback(self.active_tasks.discard)

    async def shutdown(self):
        self.is_running = False
        self.log.info("Stopping strategy, waiting for active orders to complete...")
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks)
        self.log.info("All active orders completed, shutting down...")

    def on_bookl1(self, bookl1: BookL1):
        sig = rolling_diff_sum.input((bookl1.ask + bookl1.bid) / 2)
        self.trending_signal[bookl1.symbol] = sig

    async def mock_vwap_order(
        self,
        symbol: str,
        side: OrderSide,
        amount: Decimal,
        reduce_only: bool,
        size_ratio: float = 1 / 3,
        interval: int = 1,
    ):
        self._in_ordering[symbol] = True
        self.log.debug(
            f"Mocking symbol: {symbol} side: {side} amount: {amount} reduce_only: {reduce_only}"
        )
        await asyncio.sleep(20)
        if side == OrderSide.BUY:
            self.current_positions[symbol] += amount
            self.log.debug(f"Mocked symbol: {symbol} added {amount}")
        else:
            self.current_positions[symbol] -= amount
            self.log.debug(f"Mocked symbol: {symbol} removed {amount}")
        self._save_positions(self.current_positions)
        self._in_ordering[symbol] = False

    async def vwap_order(
        self,
        symbol: str,
        side: OrderSide,
        amount: Decimal,
        reduce_only: bool,
        interval: int = 1,
        make_threshold: float = 0.4,
        amount_interval: int = 5,
        duration: int = 120,
        sigmoid_k: float = 1,
    ):
        self._in_ordering[symbol] = True
        pos = Decimal(str(0))
        on_bid = False
        order_id = None

        start = int(time.time() * 1000)  # ms
        end = start + duration * 1000  # ms

        cost = 0
        first_iter = True

        while True:
            current_time = int(time.time() * 1000)
            remaining_seconds = max((end - current_time) / 1000, 0)
            
            remaining_amount = float(amount - pos)
            if remaining_seconds == 0:
                make_ratio = 0
            else:
                process_diff_ratio = (remaining_amount / remaining_seconds) / (float(amount) / duration) - 1
                make_ratio = 1 / (1 + math.exp(sigmoid_k * process_diff_ratio))
            

            if first_iter:
                first_iter = False
            else:
                await asyncio.sleep(interval)
            if order_id:
                order: Order = await self.cache(BybitAccountType.ALL_TESTNET).get_order(
                    order_id
                )
                if order:
                    if order.status in (OrderStatus.FILLED, OrderStatus.CANCELED):
                        if pos < amount:
                            if order.status == OrderStatus.CANCELED:
                                self.log.debug(
                                    f"Symbol: {symbol} Canceled order {order_id}"
                                )
                            pos += order.filled
                            cost += order.cum_cost if order.cum_cost else 0
                            self.log.debug(f"Symbol: {symbol} Filled {pos} of {amount}")
                            order_id = None
                    else:
                        book = self.get_bookl1("bybit", symbol)
                        if (on_bid and order.price != book.bid) or (
                            not on_bid and order.price != book.ask
                        ):
                            order_cancel = await self.cancel_order(
                                account_type=BybitAccountType.ALL_TESTNET,
                                symbol=symbol,
                                order_id=order_id,
                            )
                            if not order_cancel.success:
                                self.log.debug(
                                    f"Symbol: {symbol} Failed to cancel order {order_id}"
                                )
                        else:
                            continue
            if not order_id:
                book = self.get_bookl1("bybit", symbol)

                if side == OrderSide.BUY:
                    # if self.trending_signal[symbol] > 0:
                    # if (rs := (current_time - start)/1000) > make_time:
                    if make_ratio < make_threshold:
                        self.log.debug(
                            f"Symbol: {symbol} make ratio: {make_ratio} -> take order"
                        )
                        price = book.ask
                        on_bid = False
                    else:
                        self.log.debug(
                            f"Symbol: {symbol} make ratio: {make_ratio} -> make order"
                        )
                        price = book.bid
                        on_bid = True
                elif side == OrderSide.SELL:
                    # if self.trending_signal[symbol] > 0:
                    # if (rs := (current_time - start)/1000) <= make_time:
                    if make_ratio >= make_threshold:
                        self.log.debug(
                            f"Symbol: {symbol} make ratio: {make_ratio} -> make order"
                        )
                        price = book.ask
                        on_bid = False
                    else:
                        self.log.debug(
                            f"Symbol: {symbol} make ratio: {make_ratio} -> take order"
                        )
                        price = book.bid
                        on_bid = True

                price = self.price_to_precision(
                    account_type=BybitAccountType.ALL_TESTNET,
                    symbol=symbol,
                    price=price,
                )

                remaining_interval = max(1, remaining_seconds // amount_interval)
                size = remaining_amount / remaining_interval
                self.log.debug(
                    f"Symbol: {symbol} remaining_seconds: {remaining_seconds} remaining_interval: {remaining_interval} size: {size}"
                )
                size = max(
                    self.market(BybitAccountType.ALL_TESTNET)[
                        symbol
                    ].limits.amount.min,  # min amount
                    min(size, amount - pos),
                    6 / price,  # min notional = 6
                )

                if pos < amount:
                    if reduce_only:
                        self.log.debug(
                            f"Symbol: {symbol} reduce only size: {size} amount: {amount-pos}"
                        )
                        size = min(
                            size, amount - pos
                        )  # reduce only size should be less than the remaining amount

                    size = self.amount_to_precision(
                        account_type=BybitAccountType.ALL_TESTNET,
                        symbol=symbol,
                        amount=size,
                    )

                    open_orders = await self.cache(
                        BybitAccountType.ALL_TESTNET
                    ).get_open_orders(symbol)
                    if order_id in open_orders and order_id:
                        self.log.debug(
                            f"Symbol {symbol} still have open orders: {order_id}"
                        )
                        continue
                    order = await self.create_order(
                        account_type=BybitAccountType.ALL_TESTNET,
                        symbol=symbol,
                        side=side,
                        type=OrderType.LIMIT,
                        amount=size,
                        price=price,
                        reduceOnly=reduce_only,
                    )
                    order_id = order.id
                    if order_id:
                        if not reduce_only:
                            self.log.debug(
                                f"Symbol: {symbol} Created postion: {order.id}"
                            )
                        else:
                            self.log.debug(
                                f"Symbol: {symbol} Close position: {order.id}"
                            )
                    else:
                        self.log.error(
                            f"Symbol: {symbol} Failed to create order: {order_id}"
                        )
                        for order_id in open_orders:
                            await self.cancel_order(
                                account_type=BybitAccountType.ALL_TESTNET,
                                symbol=symbol,
                                order_id=order_id,
                            )
                        break
                else:
                    self.log.debug(f"Symbol: {symbol} pos: {pos} amount: {amount}")
                    break

        position = self.fetch_positions()
        real_pos = position.get(symbol, 0)
        if side == OrderSide.BUY:
            self.log.debug(
                f"Side BUY Symbol: {symbol} pos: {self.current_positions[symbol]} + {pos} = {real_pos}"
            )
            self.current_positions[symbol] += pos
        else:
            self.log.debug(
                f"Side SELL Symbol: {symbol} pos: {self.current_positions[symbol]} - {pos} = {real_pos}"
            )
            self.current_positions[symbol] -= pos

        average = cost / float(pos) if pos > 0 else 0
        side_string = "BUY" if side == OrderSide.BUY else "SELL"
        self.log.debug(
            f"Symbol: {symbol} Side: {side_string} VWAP completed average: {average}"
        )
        self._save_positions(self.current_positions)
        self._in_ordering[symbol] = False

    async def run(self):
        for private_connector in self._private_connectors.values():
            await private_connector.connect()


def set_leverage(api: ccxt.bybit, symbol: str, leverage: int):
    try:
        api.set_leverage(leverage, symbol)
        print(f"Set leverage to {leverage} for {symbol}")
    except Exception as e:
        print(e, symbol, leverage)


async def main():
    try:
        config = {
            "apiKey": BYBIT_API_KEY,
            "secret": BYBIT_API_SECRET,
            "sandbox": True,
        }

        exchange = BybitExchangeManager(config)

        conn_linear = BybitPublicConnector(BybitAccountType.LINEAR_TESTNET, exchange)

        private_conn = BybitPrivateConnector(
            exchange,
            account_type=BybitAccountType.ALL_TESTNET,
            strategy_id="strategy_vwap",
            user_id="vip_user",
            rate_limit=20,
        )

        signal = BybitSignal(exchange.market)
        vwap = VwapStrategy(api=exchange.api)
        vwap.add_public_connector(conn_linear)
        vwap.add_private_connector(private_conn)

        signal.set_strategy(vwap)
        await signal.receive()

    except asyncio.CancelledError:
        print("Cancelled")
    finally:
        await vwap.shutdown()
        await conn_linear.disconnect()
        await private_conn.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
