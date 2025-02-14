import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
from typing import Literal
from decimal import Decimal
from decimal import ROUND_HALF_UP, ROUND_CEILING, ROUND_FLOOR

from nexustrader.schema import Order, BaseMarket
from nexustrader.core.log import SpdLog
from nexustrader.core.entity import TaskManager
from nexustrader.core.nautilius_core import MessageBus, LiveClock
from nexustrader.core.cache import AsyncCache
from nexustrader.core.registry import OrderRegistry
from nexustrader.constants import (
    AccountType,
    SubmitType,
    OrderType,
    OrderSide,
    AlgoOrderStatus,
)
from nexustrader.schema import OrderSubmit, AlgoOrder
from nexustrader.base.connector import PrivateConnector


class ExecutionManagementSystem(ABC):
    def __init__(
        self,
        market: Dict[str, BaseMarket],
        cache: AsyncCache,
        msgbus: MessageBus,
        task_manager: TaskManager,
        registry: OrderRegistry,
    ):
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )

        self._market = market
        self._cache = cache
        self._msgbus = msgbus
        self._task_manager = task_manager
        self._registry = registry
        self._clock = LiveClock()
        self._order_submit_queues: Dict[AccountType, asyncio.Queue[OrderSubmit]] = {}
        self._private_connectors: Dict[AccountType, PrivateConnector] | None = None

    def _build(self, private_connectors: Dict[AccountType, PrivateConnector]):
        self._private_connectors = private_connectors
        self._build_order_submit_queues()
        self._set_account_type()

    def _amount_to_precision(
        self,
        symbol: str,
        amount: float,
        mode: Literal["round", "ceil", "floor"] = "round",
    ) -> Decimal:
        """
        Convert the amount to the precision of the market
        """
        market = self._market[symbol]
        amount: Decimal = Decimal(str(amount))
        precision = market.precision.amount

        if precision >= 1:
            exp = Decimal(int(precision))
            precision_decimal = Decimal("1")
        else:
            exp = Decimal("1")
            precision_decimal = Decimal(str(precision))

        if mode == "round":
            format_amount = (amount / exp).quantize(
                precision_decimal, rounding=ROUND_HALF_UP
            ) * exp
        elif mode == "ceil":
            format_amount = (amount / exp).quantize(
                precision_decimal, rounding=ROUND_CEILING
            ) * exp
        elif mode == "floor":
            format_amount = (amount / exp).quantize(
                precision_decimal, rounding=ROUND_FLOOR
            ) * exp

        self._log.debug(f"{symbol} Amount to precision: {amount} -> {format_amount} {mode}")
        
        return format_amount

    def _price_to_precision(
        self,
        symbol: str,
        price: float,
        mode: Literal["round", "ceil", "floor"] = "round",
    ) -> Decimal:
        """
        Convert the price to the precision of the market
        """
        market = self._market[symbol]
        price: Decimal = Decimal(str(price))

        decimal = market.precision.price

        if decimal >= 1:
            exp = Decimal(int(decimal))
            precision_decimal = Decimal("1")
        else:
            exp = Decimal("1")
            precision_decimal = Decimal(str(decimal))

        if mode == "round":
            format_price = (price / exp).quantize(
                precision_decimal, rounding=ROUND_HALF_UP
            ) * exp
        elif mode == "ceil":
            format_price = (price / exp).quantize(
                precision_decimal, rounding=ROUND_CEILING
            ) * exp
        elif mode == "floor":
            format_price = (price / exp).quantize(
                precision_decimal, rounding=ROUND_FLOOR
            ) * exp

        self._log.debug(f"{symbol} Price to precision: {price} -> {format_price} {mode}")
        return format_price

    @abstractmethod
    def _build_order_submit_queues(self):
        """
        Build the order submit queues
        """
        pass

    @abstractmethod
    def _set_account_type(self):
        """
        Set the account type
        """
        pass

    @abstractmethod
    def _submit_order(
        self, order: OrderSubmit, account_type: AccountType | None = None
    ):
        """
        Submit an order
        """
        pass

    async def _cancel_order(self, order_submit: OrderSubmit, account_type: AccountType):
        """
        Cancel an order
        """
        order_id = self._registry.get_order_id(order_submit.uuid)
        if order_id:
            order: Order = await self._private_connectors[account_type].cancel_order(
                symbol=order_submit.symbol,
                order_id=order_id,
                **order_submit.kwargs,
            )
            order.uuid = order_submit.uuid
            if order.success:
                self._cache._order_status_update(order)  # SOME STATUS -> CANCELING
                self._msgbus.send(endpoint="canceling", msg=order)
            else:
                # self._cache._order_status_update(order) # SOME STATUS -> FAILED
                self._msgbus.send(endpoint="cancel_failed", msg=order)
            return order
        else:
            self._log.error(
                f"Order ID not found for UUID: {order_submit.uuid}, The order may already be canceled or filled or not exist"
            )

    async def _create_order(self, order_submit: OrderSubmit, account_type: AccountType):
        """
        Create an order
        """
        order: Order = await self._private_connectors[account_type].create_order(
            symbol=order_submit.symbol,
            side=order_submit.side,
            type=order_submit.type,
            amount=order_submit.amount,
            price=order_submit.price,
            time_in_force=order_submit.time_in_force,
            position_side=order_submit.position_side,
            **order_submit.kwargs,
        )
        order.uuid = order_submit.uuid
        if order.success:
            self._registry.register_order(order)
            self._cache._order_initialized(order)  # INITIALIZED -> PENDING
            self._msgbus.send(endpoint="pending", msg=order)
        else:
            self._cache._order_status_update(order)  # INITIALIZED -> FAILED
            self._msgbus.send(endpoint="failed", msg=order)
        return order

    async def _create_stop_loss_order(
        self, order_submit: OrderSubmit, account_type: AccountType
    ):
        """
        Create a stop loss order
        """
        order: Order = await self._private_connectors[
            account_type
        ].create_stop_loss_order(
            symbol=order_submit.symbol,
            side=order_submit.side,
            type=order_submit.type,
            amount=order_submit.amount,
            trigger_type=order_submit.trigger_type,
            trigger_price=order_submit.trigger_price,
            price=order_submit.price,
            time_in_force=order_submit.time_in_force,
            position_side=order_submit.position_side,
            **order_submit.kwargs,
        )
        order.uuid = order_submit.uuid
        if order.success:
            self._registry.register_order(order)
            self._cache._order_initialized(order)  # INITIALIZED -> PENDING
            self._msgbus.send(endpoint="pending", msg=order)
        else:
            self._cache._order_status_update(order)  # INITIALIZED -> FAILED
            self._msgbus.send(endpoint="failed", msg=order)
        return order

    async def _create_take_profit_order(
        self, order_submit: OrderSubmit, account_type: AccountType
    ) -> Order:
        """
        Create a take profit order
        """
        order: Order = await self._private_connectors[
            account_type
        ].create_take_profit_order(
            symbol=order_submit.symbol,
            side=order_submit.side,
            type=order_submit.type,
            amount=order_submit.amount,
            trigger_price=order_submit.trigger_price,
            trigger_type=order_submit.trigger_type,
            price=order_submit.price,
            time_in_force=order_submit.time_in_force,
            position_side=order_submit.position_side,
            **order_submit.kwargs,
        )
        order.uuid = order_submit.uuid
        if order.success:
            self._registry.register_order(order)
            self._cache._order_initialized(order)  # INITIALIZED -> PENDING
            self._msgbus.send(endpoint="pending", msg=order)
        else:
            self._cache._order_status_update(order)  # INITIALIZED -> FAILED
            self._msgbus.send(endpoint="failed", msg=order)
        return order

    @abstractmethod
    def _get_min_order_amount(self, symbol: str, market: BaseMarket) -> Decimal:
        """
        Get the minimum order amount
        """
        pass

    def _calculate_twap_orders(
        self,
        symbol: str,
        total_amount: Decimal,
        duration: float,
        wait: float,
        min_order_amount: Decimal,
    ) -> Tuple[List[Decimal], float]:
        """
        Calculate the amount list and wait time for the twap order

        eg:
        amount_list = [10, 10, 10]
        wait = 10
        """
        amount_list = []
        if total_amount == 0 or total_amount < min_order_amount:
            self._log.info(
                f"TWAP ORDER: {symbol} Total amount is less than min order amount: {total_amount} < {min_order_amount}"
            )
            return [], 0

        interval = duration // wait
        base_amount = float(total_amount) / interval

        base_amount = max(
            min_order_amount, self._amount_to_precision(symbol, base_amount)
        )

        interval = int(total_amount // base_amount)
        remaining = total_amount - interval * base_amount

        if remaining < min_order_amount:
            amount_list = [base_amount] * interval
            amount_list[-1] += remaining
        else:
            amount_list = [base_amount] * interval + [remaining]

        wait = duration / len(amount_list)
        return amount_list, wait

    def _cal_limit_order_price(
        self, symbol: str, side: OrderSide, market: BaseMarket
    ) -> Decimal:
        """
        Calculate the limit order price
        """
        basis_point = market.precision.price
        book = self._cache.bookl1(symbol)

        if side.is_buy:
            # if the spread is greater than the basis point
            if book.spread > basis_point:
                price = book.ask - basis_point
            else:
                price = book.bid
        elif side.is_sell:
            # if the spread is greater than the basis point
            if book.spread > basis_point:
                price = book.bid + basis_point
            else:
                price = book.ask
        return self._price_to_precision(symbol, price)

    def _cal_filled_info(self, order_ids: List[str]) -> Dict[str, Decimal | float]:
        """
        Calculate the filled info
        """
        filled = Decimal(0)
        cost = 0
        for order_id in order_ids:
            order = self._cache.get_order(order_id).unwrap()
            if order.is_closed:
                filled += order.filled
                cost += order.average * float(order.filled)

        if filled == 0:
            return {
                "filled": Decimal(0),
                "cost": 0,
                "average": 0,
            }

        average = cost / float(filled)
        return {
            "filled": filled,
            "cost": cost,
            "average": average,
        }

    async def _adp_maker_order(
        self, order_submit: OrderSubmit, account_type: AccountType
    ):
        """
        adaptive maker order
        make first, if not filled, then take the order
        """
        symbol = order_submit.symbol
        instrument_id = order_submit.instrument_id
        side = order_submit.side
        market = self._market[symbol]
        amount: Decimal = order_submit.amount
        position_side = order_submit.position_side 
        kwargs = order_submit.kwargs
        check_interval = order_submit.check_interval  # seconds
        wait = order_submit.wait  # seconds
        duration = order_submit.duration  # seconds
        adp_maker_order_uuid = order_submit.uuid
        trigger_tp_ratio = order_submit.trigger_tp_ratio
        trigger_sl_ratio = order_submit.trigger_sl_ratio
        tp_ratio = order_submit.tp_ratio
        sl_ratio = order_submit.sl_ratio
        min_order_amount: Decimal = self._get_min_order_amount(symbol, market)

        # 0) initialize the algo order
        algo_order = AlgoOrder(
            symbol=symbol,
            uuid=adp_maker_order_uuid,
            side=side,
            amount=amount,
            duration=duration,
            wait=wait,
            status=AlgoOrderStatus.RUNNING,
            exchange=instrument_id.exchange,
            timestamp=self._clock.timestamp_ms(),
            position_side=position_side,
        )

        self._cache._order_initialized(algo_order)

        # 1) check the amount
        if amount < min_order_amount:
            algo_order.status = AlgoOrderStatus.FAILED
            self._cache._order_status_update(algo_order)
            self._log.error(
                f"ADAPTIVE MAKER ORDER FAILED: symbol: {symbol}, side: {side}, uuid: {adp_maker_order_uuid}"
            )
            return

        try:
            # 2) create maker order
            price = self._cal_limit_order_price(symbol, side, market)
            order = await self._create_order(
                order_submit=OrderSubmit(
                    symbol=symbol,
                    instrument_id=instrument_id,
                    submit_type=SubmitType.CREATE,
                    side=side,
                    type=OrderType.LIMIT,
                    amount=amount,
                    price=price,
                    position_side=position_side,
                    kwargs=kwargs,
                ),
                account_type=account_type,
            )

            # 3) check the order is success
            if not order.success:
                algo_order.status = AlgoOrderStatus.FAILED
                self._cache._order_status_update(algo_order)
                self._log.error(
                    f"ADAPTIVE MAKER ORDER FAILED: symbol: {symbol}, side: {side}, uuid: {order_submit.uuid}"
                )
                return

            order_id = order.uuid
            algo_order.orders.append(order_id)

            # 4) wait for the order to be filled
            await asyncio.sleep(wait)

            # 5) check the order the order status and the book price
            # 5.1) if side.is_buy and bid > price, then cancel the order
            # 5.2) if side.is_sell and ask < price, then cancel the order
            start_time = self._clock.timestamp_ms()
            while True:
                order = self._cache.get_order(order_id)  # Maybe[Order]
                is_opened = order.bind_optional(lambda order: order.is_opened).value_or(
                    False
                )
                on_flight = order.bind_optional(lambda order: order.on_flight).value_or(
                    False
                )
                is_closed = order.bind_optional(lambda order: order.is_closed).value_or(
                    False
                )
                self._log.debug(
                    f"ADAPTIVE MAKER ORDER: status: {order.unwrap().status}, is_opened: {is_opened}, on_flight: {on_flight}, is_closed: {is_closed}"
                )
                if is_opened and not on_flight:
                    book = self._cache.bookl1(symbol)
                    if (
                        side.is_buy
                        and book.bid > price
                        or side.is_sell
                        and book.ask < price
                    ) or self._clock.timestamp_ms() - start_time > (
                        duration - wait
                    ) * 1000:
                        await self._cancel_order(
                            order_submit=OrderSubmit(
                                symbol=symbol,
                                instrument_id=instrument_id,
                                submit_type=SubmitType.CANCEL,
                                uuid=order_id,
                            ),
                            account_type=account_type,
                        )
                elif is_closed:
                    # 6) closed has 2 status: FILLED and CANCELED
                    # 6.1) if FILLED, then remaining amount is 0 -> break
                    # 6.2) if CANCELED, then check the remaining amount
                    # 6.3) if remaining amount is greater than min order amount, then create a market order
                    # 6.4) if remaining amount is less than min order amount, then break
                    # 6.5) if reduce_only is True, then no need to follow the min order amount filter
                    remaining = order.unwrap().remaining
                    if remaining > min_order_amount or 'reduce_only' in kwargs: 
                        order_take = await self._create_order(
                            order_submit=OrderSubmit(
                                symbol=symbol,
                                instrument_id=instrument_id,
                                submit_type=SubmitType.CREATE,
                                side=side,
                                type=OrderType.MARKET,
                                amount=remaining,
                                position_side=position_side,
                                kwargs=kwargs,
                            ),
                            account_type=account_type,
                        )

                        if order_take.success:
                            algo_order.orders.append(order_take.uuid)

                            # 6.5) wait for the order to be closed
                            while True:
                                take_order = self._cache.get_order(order_take.uuid)
                                is_closed = take_order.bind_optional(
                                    lambda order: order.is_closed
                                ).value_or(False)
                                if is_closed:
                                    break
                                await asyncio.sleep(check_interval)
                    break
                await asyncio.sleep(check_interval)

            # 7) calculate the make ratio and update the algo order status
            make_ratio = 1 - float(remaining) / float(amount)
            algo_order.make_ratio = make_ratio

            # 8) calculate the filled info
            filled_info = self._cal_filled_info(algo_order.orders)
            algo_order.filled = filled_info["filled"]
            algo_order.cost = filled_info["cost"]
            algo_order.average = filled_info["average"]
            self._log.debug(
                f"ADAPTIVE MAKER ORDER: symbol: {symbol}, side: {side}, uuid: {adp_maker_order_uuid} filled: {algo_order.filled}, cost: {algo_order.cost}, average: {algo_order.average}"
            )

            # 9) add tp and sl orders
            if (price := algo_order.average) > 0:
                if trigger_tp_ratio:
                    if side.is_buy:
                        _trigger_tp_ratio = 1 + trigger_tp_ratio
                        _tp_ratio = 1 + tp_ratio
                        mode = "ceil"
                    else:
                        _trigger_tp_ratio = 1 - trigger_tp_ratio
                        _tp_ratio = 1 - tp_ratio
                        mode = "floor"

                    trigger_price = self._price_to_precision(
                        symbol, price * _trigger_tp_ratio, mode=mode
                    )
                    
                    # for buy -> trigger_price > ask
                    # for sell -> trigger_price < bid
                    book = self._cache.bookl1(symbol)
                    if trigger_price < book.ask and side.is_buy:
                        self._log.debug(f"symbol: {symbol}, side: {side}, uuid: {adp_maker_order_uuid}, modify trigger price to ask: {trigger_price} -> {book.ask}")
                        trigger_price = book.ask
                    elif trigger_price > book.bid and side.is_sell:
                        self._log.debug(f"symbol: {symbol}, side: {side}, uuid: {adp_maker_order_uuid}, modify trigger price to bid: {trigger_price} -> {book.bid}")
                        trigger_price = book.bid

                    if tp_ratio:
                        tp_price = self._price_to_precision(symbol, price * _tp_ratio, mode=mode)

                    tp_order = await self._create_take_profit_order(
                        order_submit=OrderSubmit(
                            symbol=symbol,
                            instrument_id=instrument_id,
                            submit_type=SubmitType.TAKE_PROFIT,
                            side=OrderSide.SELL if side.is_buy else OrderSide.BUY,
                            type=OrderType.TAKE_PROFIT_LIMIT
                            if tp_ratio
                            else OrderType.TAKE_PROFIT_MARKET,
                            amount=algo_order.filled,
                            price=tp_price,
                            trigger_price=trigger_price,
                            kwargs={"reduce_only": True},
                        ),
                        account_type=account_type,
                    )

                    if tp_order.success:
                        self._log.debug(
                            f"ADAPTIVE MAKER ORDER: symbol: {symbol}, side: {side}, uuid: {adp_maker_order_uuid} create tp trigger price: {trigger_price}, tp price: {tp_price}"
                        )
                        algo_order.tp_orders.append(tp_order.uuid)
                    else:
                        self._log.error(
                            f"ADAPTIVE MAKER ORDER: symbol: {symbol}, side: {side}, uuid: {adp_maker_order_uuid} create tp order failed"
                        )

                if trigger_sl_ratio:
                    if side.is_buy:
                        _trigger_sl_ratio = 1 - trigger_sl_ratio
                        _sl_ratio = 1 - sl_ratio
                        mode = "floor"
                    else:
                        _trigger_sl_ratio = 1 + trigger_sl_ratio
                        _sl_ratio = 1 + sl_ratio
                        mode = "ceil"

                    trigger_price = self._price_to_precision(
                        symbol, price * _trigger_sl_ratio, mode=mode
                    )
                    
                    # for buy -> trigger_price < ask
                    # for sell -> trigger_price > bid
                    book = self._cache.bookl1(symbol)
                    if trigger_price > book.bid and side.is_buy:
                        self._log.debug(f"symbol: {symbol}, side: {side}, uuid: {adp_maker_order_uuid}, modify trigger price to bid: {trigger_price} -> {book.bid}")
                        trigger_price = book.bid
                    elif trigger_price < book.ask and side.is_sell:
                        self._log.debug(f"symbol: {symbol}, side: {side}, uuid: {adp_maker_order_uuid}, modify trigger price to ask: {trigger_price} -> {book.ask}")
                        trigger_price = book.ask

                    if sl_ratio:
                        sl_price = self._price_to_precision(symbol, price * _sl_ratio, mode=mode)

                    sl_order = await self._create_stop_loss_order(
                        order_submit=OrderSubmit(
                            symbol=symbol,
                            instrument_id=instrument_id,
                            submit_type=SubmitType.STOP_LOSS,
                            side=OrderSide.SELL if side.is_buy else OrderSide.BUY,
                            amount=algo_order.filled,
                            type=OrderType.STOP_LOSS_LIMIT
                            if sl_ratio
                            else OrderType.STOP_LOSS_MARKET,
                            price=sl_price,
                            trigger_price=trigger_price,
                            kwargs={"reduce_only": True},
                        ),
                        account_type=account_type,
                    )

                    if sl_order.success:
                        self._log.debug(
                            f"ADAPTIVE MAKER ORDER: symbol: {symbol}, side: {side}, uuid: {adp_maker_order_uuid} create sl trigger price: {trigger_price}, sl price: {sl_price}"
                        )
                        algo_order.sl_orders.append(sl_order.uuid)
                    else:
                        self._log.error(
                            f"ADAPTIVE MAKER ORDER: symbol: {symbol}, side: {side}, uuid: {adp_maker_order_uuid} create sl order failed"
                        )

            algo_order.status = AlgoOrderStatus.FINISHED
            self._cache._order_status_update(algo_order)
        except asyncio.CancelledError:
            algo_order.status = AlgoOrderStatus.CANCELING
            self._cache._order_status_update(algo_order)

            open_orders = self._cache.get_open_orders(symbol=symbol)
            for uuid in open_orders.copy():
                await self._cancel_order(
                    order_submit=OrderSubmit(
                        symbol=symbol,
                        instrument_id=instrument_id,
                        submit_type=SubmitType.CANCEL,
                        uuid=uuid,
                    ),
                    account_type=account_type,
                )

            filled_info = self._cal_filled_info(algo_order.orders)
            algo_order.filled = filled_info["filled"]
            algo_order.cost = filled_info["cost"]
            algo_order.average = filled_info["average"]

            algo_order.status = AlgoOrderStatus.CANCELED
            self._cache._order_status_update(algo_order)

            self._log.debug(
                f"ADAPTIVE MAKER ORDER CANCELLED: symbol: {symbol}, side: {side}, uuid: {adp_maker_order_uuid}"
            )

    async def _twap_order(self, order_submit: OrderSubmit, account_type: AccountType):
        """
        Execute the twap order
        """
        symbol = order_submit.symbol
        instrument_id = order_submit.instrument_id
        side = order_submit.side
        market = self._market[symbol]
        position_side = order_submit.position_side
        kwargs = order_submit.kwargs
        twap_uuid = order_submit.uuid
        check_interval = order_submit.check_interval

        algo_order = AlgoOrder(
            symbol=symbol,
            uuid=twap_uuid,
            side=side,
            amount=order_submit.amount,
            duration=order_submit.duration,
            wait=order_submit.wait,
            status=AlgoOrderStatus.RUNNING,
            exchange=instrument_id.exchange,
            timestamp=self._clock.timestamp_ms(),
            position_side=position_side,
        )

        self._cache._order_initialized(algo_order)

        min_order_amount: Decimal = self._get_min_order_amount(symbol, market)
        amount_list, wait = self._calculate_twap_orders(
            symbol=symbol,
            total_amount=order_submit.amount,
            duration=order_submit.duration,
            wait=order_submit.wait,
            min_order_amount=min_order_amount,
        )

        self._log.debug(
            f"amount_list: {amount_list}, min_order_amount: {min_order_amount}, wait: {wait}"
        )

        order_id = None
        elapsed_time = 0

        try:
            while amount_list:
                if order_id:
                    order = self._cache.get_order(order_id)

                    is_opened = order.bind_optional(
                        lambda order: order.is_opened
                    ).value_or(False)
                    on_flight = order.bind_optional(
                        lambda order: order.on_flight
                    ).value_or(False)
                    is_closed = order.bind_optional(
                        lambda order: order.is_closed
                    ).value_or(False)

                    # 检查现价单是否已成交，不然的话立刻下市价单成交 或者 把remaining amount加到下一个市价单上
                    if is_opened and not on_flight:
                        await self._cancel_order(
                            order_submit=OrderSubmit(
                                symbol=symbol,
                                instrument_id=instrument_id,
                                submit_type=SubmitType.CANCEL,
                                uuid=order_id,
                            ),
                            account_type=account_type,
                        )
                        self._log.debug(f"CANCEL: {order.unwrap()}")
                    elif is_closed:
                        order_id = None
                        # amount = amount_list.pop()
                        remaining = order.unwrap().remaining
                        if remaining > min_order_amount:
                            order = await self._create_order(
                                order_submit=OrderSubmit(
                                    symbol=symbol,
                                    instrument_id=instrument_id,
                                    submit_type=SubmitType.CREATE,
                                    side=side,
                                    type=OrderType.MARKET,
                                    amount=remaining,
                                    position_side=position_side,
                                    kwargs=kwargs,
                                ),
                                account_type=account_type,
                            )
                            if order.success:
                                algo_order.orders.append(order.uuid)
                                self._cache._order_status_update(algo_order)
                            else:
                                algo_order.status = AlgoOrderStatus.FAILED
                                self._cache._order_status_update(algo_order)
                                self._log.error(
                                    f"TWAP ORDER FAILED: symbol: {symbol}, side: {side}"
                                )
                                break
                        else:
                            if amount_list:
                                amount_list[-1] += remaining
                    else:
                        await asyncio.sleep(check_interval)
                        elapsed_time += check_interval
                else:
                    price = self._cal_limit_order_price(
                        symbol=symbol,
                        side=side,
                        market=market,
                    )
                    amount = amount_list.pop()
                    if amount_list:
                        order_submit = OrderSubmit(
                            symbol=symbol,
                            instrument_id=instrument_id,
                            submit_type=SubmitType.CREATE,
                            type=OrderType.LIMIT,
                            side=side,
                            amount=amount,
                            price=price,
                            position_side=position_side,
                            kwargs=kwargs,
                        )
                    else:
                        order_submit = OrderSubmit(
                            symbol=symbol,
                            instrument_id=instrument_id,
                            submit_type=SubmitType.CREATE,
                            type=OrderType.MARKET,
                            side=side,
                            amount=amount,
                            position_side=position_side,
                            kwargs=kwargs,
                        )
                    order = await self._create_order(order_submit, account_type)
                    if order.success:
                        order_id = order.uuid
                        algo_order.orders.append(order_id)
                        self._cache._order_status_update(algo_order)
                        await asyncio.sleep(wait - elapsed_time)
                        elapsed_time = 0
                    else:
                        algo_order.status = AlgoOrderStatus.FAILED
                        self._cache._order_status_update(algo_order)

                        self._log.error(
                            f"TWAP ORDER FAILED: symbol: {symbol}, side: {side}, uuid: {twap_uuid}"
                        )
                        break

            algo_order.status = AlgoOrderStatus.FINISHED
            self._cache._order_status_update(algo_order)

            self._log.debug(
                f"TWAP ORDER FINISHED: symbol: {symbol}, side: {side}, uuid: {twap_uuid}"
            )
        except asyncio.CancelledError:
            algo_order.status = AlgoOrderStatus.CANCELING
            self._cache._order_status_update(algo_order)

            open_orders = self._cache.get_open_orders(symbol=symbol)
            for uuid in open_orders.copy():
                await self._cancel_order(
                    order_submit=OrderSubmit(
                        symbol=symbol,
                        instrument_id=instrument_id,
                        submit_type=SubmitType.CANCEL,
                        uuid=uuid,
                    ),
                    account_type=account_type,
                )

            algo_order.status = AlgoOrderStatus.CANCELED
            self._cache._order_status_update(algo_order)

            self._log.debug(
                f"TWAP ORDER CANCELLED: symbol: {symbol}, side: {side}, uuid: {twap_uuid}"
            )

    async def _create_adp_maker_order(
        self, order_submit: OrderSubmit, account_type: AccountType
    ):
        """
        Create an adp maker order
        """
        uuid = order_submit.uuid
        self._task_manager.create_task(
            self._adp_maker_order(order_submit, account_type), name=uuid
        )

    async def _cancel_adp_maker_order(
        self, order_submit: OrderSubmit, account_type: AccountType
    ):
        """
        Cancel an adp maker order
        """
        uuid = order_submit.uuid
        self._task_manager.cancel_task(uuid)

    async def _create_twap_order(
        self, order_submit: OrderSubmit, account_type: AccountType
    ):
        """
        Create a twap order
        """
        uuid = order_submit.uuid
        self._task_manager.create_task(
            self._twap_order(order_submit, account_type), name=uuid
        )

    async def _cancel_twap_order(
        self, order_submit: OrderSubmit, account_type: AccountType
    ):
        """
        Cancel a twap order
        """
        uuid = order_submit.uuid
        self._task_manager.cancel_task(uuid)

    async def _handle_submit_order(
        self, account_type: AccountType, queue: asyncio.Queue[OrderSubmit]
    ):
        """
        Handle the order submit
        """
        submit_handlers = {
            SubmitType.CANCEL: self._cancel_order,
            SubmitType.CREATE: self._create_order,
            SubmitType.TWAP: self._create_twap_order,
            SubmitType.CANCEL_TWAP: self._cancel_twap_order,
            SubmitType.STOP_LOSS: self._create_stop_loss_order,
            SubmitType.TAKE_PROFIT: self._create_take_profit_order,
            SubmitType.ADP_MAKER: self._create_adp_maker_order,
            SubmitType.CANCEL_ADP_MAKER: self._cancel_adp_maker_order,
        }

        self._log.debug(f"Handling orders for account type: {account_type}")
        while True:
            order_submit = await queue.get()
            self._log.debug(f"[ORDER SUBMIT]: {order_submit}")
            handler = submit_handlers[order_submit.submit_type]
            await handler(order_submit, account_type)
            queue.task_done()

    async def start(self):
        """
        Start the order submit
        """
        for account_type in self._order_submit_queues.keys():
            self._task_manager.create_task(
                self._handle_submit_order(
                    account_type, self._order_submit_queues[account_type]
                )
            )
