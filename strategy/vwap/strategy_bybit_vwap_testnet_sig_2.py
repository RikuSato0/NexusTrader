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
from tradebot.constants import KEYS
from tradebot.types import Order, BookL1
from tradebot.constants import OrderSide, OrderType, OrderStatus
from tradebot.strategy import Strategy
from tradebot.exchange.bybit.types import BybitMarket
from decimal import Decimal
from tradebot.core.entity import EventSystem
from tradebot.exchange.bybit import (
    BybitPublicConnector,
    BybitPrivateConnector,
    BybitAccountType,
    BybitExchangeManager,
)

DIR_PATH = os.path.dirname(os.path.abspath(__file__))

BYBIT_API_KEY = KEYS["bybit_testnet_2"]["API_KEY"]
BYBIT_API_SECRET = KEYS["bybit_testnet_2"]["SECRET"]


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
            p["symbol"]: Decimal(str((-1 if p["side"] == "short" else 1)
            * p["contracts"]
            * p["contractSize"]))
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
                # pos = Decimal(str(0))
                reduce_only = False
            amount = pos - current_pos
            self.log.debug(f"target pos: {pos} current pos: {current_pos} side: {side} amount: {amount} reduce_only: {reduce_only}")
            return side, amount, reduce_only
        elif pos - current_pos < 0:
            side = OrderSide.SELL
            if pos < 0 and current_pos <= 0:
                reduce_only = False
            elif pos >= 0 and current_pos > 0:
                reduce_only = True
            else:
                # pos = Decimal(str(0))
                reduce_only = False
            amount = current_pos - pos
            self.log.debug(f"target pos: {pos} current pos: {current_pos} side: {side} amount: {amount} reduce_only: {reduce_only}")
            return side, amount, reduce_only

    async def on_signal(self, positions: Dict[str, Dict]):
        if not self.is_running:
            return

        for symbol, pos in positions.items():
            res = self._get_order_params(symbol, pos)
            if res:
                side, amount, reduce_only = res
                if not self._in_ordering[symbol]:
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
        await asyncio.sleep(3)
        if side == OrderSide.BUY:
            self.current_positions[symbol] += amount
            self.log.debug(f"Mocked symbol: {symbol} added {amount}")
        else:
            self.current_positions[symbol] -= amount
            self.log.debug(f"Mocked symbol: {symbol} removed {amount}")
        self._save_positions(self.current_positions)
        self._in_ordering[symbol] = False

    def amount_check(
        self, symbol: str, amount: Decimal, price: float, remaining: Decimal
    ):
        min_usdt = 5
        min_amount_filter = self.market(BybitAccountType.ALL_TESTNET)[
            symbol
        ].limits.amount.min
        min_notional_filter = min_usdt / price

        if float(amount) < min_amount_filter or float(remaining) < min_amount_filter:
            self.log.debug(
                f"Symbol: {symbol} amount: {amount} remaining: {remaining} min_amount_filter: {min_amount_filter}"
            )
            return False
        if (
            float(amount) < min_notional_filter
            or float(remaining) < min_notional_filter
        ):
            self.log.debug(
                f"Symbol: {symbol} amount: {amount} remaining: {remaining} min_notional_filter: {min_notional_filter}"
            )
            return False
        return True
    
    def interval_calc(self, symbol: str, amount: Decimal, duration: int, price: float):
        """
        20 / price = interval_amount 
        
        num_interval = max(1, amount / interval_amount)
        interval_duration = duration / num_interval
        """
        min_amount = self.market(BybitAccountType.ALL_TESTNET)[symbol].limits.amount.min
        interval_amount = max(40 / price, 4*min_amount)
        num_interval = max(1, float(amount) / interval_amount)
        interval_duration = duration / num_interval
        return interval_duration
    
    async def cal_pos_diff(self, symbol):
        pos = self.current_positions[symbol]
        pos_obj = await self.cache(BybitAccountType.ALL_TESTNET).get_position(symbol)
        if pos_obj:
            real_pos = pos_obj.signed_amount
        return abs(real_pos - pos)
        

    async def vwap_order(
        self,
        symbol: str,
        side: OrderSide,
        amount: Decimal,
        reduce_only: bool,
        interval: int = 1,  # seconds
        duration: int = 120,  # seconds
        sigmoid_k: float = 1,
    ):
        self._in_ordering[symbol] = True
        pos = Decimal(str(0))

        make_order_id = None
        take_order_id = None

        start = int(time.time())
        end = start + duration
        
        book = self.get_bookl1("bybit", symbol)
        price = (book.ask + book.bid) / 2
        
        interval_duration = self.interval_calc(symbol, amount, duration, price)
        self.log.debug(f"Symbol: {symbol} interval_duration: {interval_duration}s")
        
        cost = 0
        
        while True:
            current_time = int(time.time())
            remaing_time = max(0, end - current_time)

            remaing_amount = float(amount - pos)

            if remaing_time == 0:
                make_t = 0
            else:
                diff_ratio = (remaing_amount / float(amount)) / (
                    remaing_time / duration
                ) - 1
                make_t = 1 / (1 + math.exp(sigmoid_k * diff_ratio))

            remaining_interval = max(1, remaing_time / interval_duration)
            interval_amount = remaing_amount / remaining_interval

            interval_amount = self.amount_to_precision(
                account_type=BybitAccountType.ALL_TESTNET,
                symbol=symbol,
                amount=interval_amount,
            )

            amount_make = float(interval_amount) * make_t
            amount_make = self.amount_to_precision(
                account_type=BybitAccountType.ALL_TESTNET,
                symbol=symbol,
                amount=amount_make,
            )
            amount_take = interval_amount - amount_make

            self.log.debug(
                f"Symbol: {symbol} make_t: {make_t} remaining_interval: {remaining_interval} interval_amount: {interval_amount} amount_make: {amount_make} amount_take: {amount_take}"
            )

            remaing_amount_make = remaing_amount * make_t
            remaing_amount_make = self.amount_to_precision(
                account_type=BybitAccountType.ALL_TESTNET,
                symbol=symbol,
                amount=remaing_amount_make,
            )
            remaing_amount_take = (amount-pos) - remaing_amount_make

            book = self.get_bookl1("bybit", symbol)
            ask_price, bid_price = book.ask, book.bid

            if side == OrderSide.BUY:
                price_make, price_take = bid_price, ask_price
            elif side == OrderSide.SELL:
                price_make, price_take = ask_price, bid_price

            if remaing_amount > 0:
                if remaining_interval > 1:
                    if not make_order_id and self.amount_check(
                        symbol, amount_make, price_make, remaing_amount_make
                    ):
                        make_order = await self.create_order(
                            account_type=BybitAccountType.ALL_TESTNET,
                            symbol=symbol,
                            side=side,
                            type=OrderType.LIMIT,
                            amount=amount_make,
                            price=price_make,
                            reduce_only=reduce_only,
                        )
                        make_order_id = make_order.id

                        if make_order_id:
                            self.log.debug(
                                f"[{'CLOSE' if reduce_only else 'OPEN'}] Symbol: {symbol} Make order id: {make_order_id}"
                            )

                    if not take_order_id and self.amount_check(
                        symbol, amount_take, price_take, remaing_amount_take
                    ):
                        take_order = await self.create_order(
                            account_type=BybitAccountType.ALL_TESTNET,
                            symbol=symbol,
                            side=side,
                            type=OrderType.LIMIT,
                            amount=amount_take,
                            price=price_take,
                            reduce_only=reduce_only,
                        )
                        take_order_id = take_order.id

                        if take_order_id:
                            self.log.debug(
                                f"[{'CLOSE' if reduce_only else 'OPEN'}] Symbol: {symbol} Take order id: {take_order_id}"
                            )
                elif remaining_interval == 1:
                    if not take_order_id and not make_order_id and self.amount_check(
                        symbol, interval_amount, price_take, remaing_amount
                    ):
                        take_order = await self.create_order(
                            account_type=BybitAccountType.ALL_TESTNET,
                            symbol=symbol,
                            side=side,
                            type=OrderType.MARKET,
                            amount=interval_amount,
                            reduce_only=reduce_only,
                        )
                        take_order_id = take_order.id
                        if take_order_id:
                            self.log.debug(
                                f"[{'CLOSE' if reduce_only else 'OPEN'}] Symbol: {symbol} Take order id: {take_order_id}"
                            )       
            else:
                self.log.debug(f"Symbol: {symbol} pos: {pos} amount: {amount} Finished")
                break

            if make_order_id:
                make_order: Order = await self.cache(
                    BybitAccountType.ALL_TESTNET
                ).get_order(make_order_id)
                if make_order:
                    if make_order.status in (OrderStatus.FILLED, OrderStatus.CANCELED):
                        if pos < amount:
                            if make_order.status == OrderStatus.CANCELED:
                                self.log.debug(
                                    f"Symbol: {symbol} Canceled order {make_order_id}"
                                )
                            pos += make_order.filled
                            cost += make_order.cum_cost if make_order.cum_cost else 0
                            diff = await self.cal_pos_diff(symbol)
                            self.log.debug(
                                f"Symbol: {symbol} Make Filled {pos}/{amount} Make Order id: {make_order_id} diff: {diff}"
                            )
                            make_order_id = None
                    else:
                        book = self.get_bookl1("bybit", symbol)
                        if (
                            (side == OrderSide.BUY and make_order.price != book.bid)
                            or (side == OrderSide.SELL and make_order.price != book.ask)
                            or (make_order.amount != amount_make)
                        ):
                            make_order_cancel = await self.cancel_order(
                                account_type=BybitAccountType.ALL_TESTNET,
                                symbol=symbol,
                                order_id=make_order_id,
                            )
                            if not make_order_cancel.success:
                                self.log.debug(
                                    f"Symbol: {symbol} Failed to cancel make order {make_order_id}"
                                )

            if take_order_id:
                take_order: Order = await self.cache(
                    BybitAccountType.ALL_TESTNET
                ).get_order(take_order_id)
                if take_order:
                    if take_order.status in (OrderStatus.FILLED, OrderStatus.CANCELED):
                        if pos < amount:
                            if take_order.status == OrderStatus.CANCELED:
                                self.log.debug(
                                    f"Symbol: {symbol} Canceled order {take_order_id}"
                                )
                            pos += take_order.filled
                            cost += take_order.cum_cost if take_order.cum_cost else 0
                            diff = await self.cal_pos_diff(symbol)
                            self.log.debug(
                                f"Symbol: {symbol} Take Filled {pos}/{amount} Take Order id: {take_order_id} diff: {diff}"
                            )
                            take_order_id = None
                    else:
                        book = self.get_bookl1("bybit", symbol)
                        if (
                            (side == OrderSide.BUY and take_order.price != book.ask)
                            or (side == OrderSide.SELL and take_order.price != book.bid)
                            or (take_order.amount != amount_take)
                        ):
                            take_order_cancel = await self.cancel_order(
                                account_type=BybitAccountType.ALL_TESTNET,
                                symbol=symbol,
                                order_id=take_order_id,
                            )
                            if not take_order_cancel.success:
                                self.log.debug(
                                    f"Symbol: {symbol} Failed to cancel make order {take_order_id}"
                                )

            await asyncio.sleep(interval)
        position = self.fetch_positions()
        real_pos = position.get(symbol, Decimal(str(0)))
        pos_obj = await self.cache(BybitAccountType.ALL_TESTNET).get_position(symbol)
        
        real_pos_2 = pos_obj.signed_amount
        if real_pos_2 != real_pos:
            self.log.error(f"Symbol: {symbol} BUY pos mismatch {real_pos_2} != {real_pos}")
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
        average = (cost / float(pos)) if pos > 0 else 0
        side_string = "BUY" if side == OrderSide.BUY else "SELL"
        self.log.debug(f"Symbol: {symbol} Side: {side_string} VWAP completed average: {average}")
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
