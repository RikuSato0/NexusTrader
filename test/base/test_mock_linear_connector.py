import pytest
import time
from decimal import Decimal
from copy import copy
from nexustrader.schema import Order, ExchangeType, BookL1, Kline, Trade, Position, PositionSide, Balance
from nexustrader.constants import OrderStatus, OrderSide, OrderType, KlineInterval
from nexustrader.core.cache import AsyncCache
from nexustrader.exchange.binance.constants import BinanceAccountType
from nexustrader.base import MockLinearConnector



@pytest.fixture
async def mock_linear_connector(exchange, task_manager, message_bus, cache):
    mock_linear_connector = MockLinearConnector(
        initial_balance={
            "USDT": 10000,
            "BTC": 0,
        },
        account_type=BinanceAccountType.LINEAR_MOCK,
        exchange=exchange,
        msgbus=message_bus,
        cache=cache,
        task_manager=task_manager,
        overwrite_balance=True,
        fee_rate=0.0005,
        quote_currency="USDT",
        update_interval=60,
        leverage=1,
    )
    return mock_linear_connector


async def test_create_order_failed_with_no_market(mock_linear_connector: MockLinearConnector):
    order = await mock_linear_connector.create_order(
        symbol="BTC-USD",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        amount=1,
    )
    assert order.status == OrderStatus.FAILED

async def test_create_order_failed_with_not_linear_contract(mock_linear_connector: MockLinearConnector):
    order = await mock_linear_connector.create_order(
        symbol="BTCUSDT.BINANCE",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        amount=1,
    )
    assert order.status == OrderStatus.FAILED

async def test_create_order_failed_with_not_enough_balance(mock_linear_connector: MockLinearConnector):
    await mock_linear_connector._cache._init_storage()
    mock_linear_connector._init_balance()
    mock_linear_connector._init_position()
    order = await mock_linear_connector.create_order(
        symbol="BTCUSDC-PERP.BINANCE",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        amount=1,
    )
    assert order.status == OrderStatus.FAILED

async def test_create_order_failed_with_not_enough_margin(mock_linear_connector: MockLinearConnector):
    await mock_linear_connector._cache._init_storage()
    mock_linear_connector._init_balance()
    mock_linear_connector._init_position()
    order = await mock_linear_connector.create_order(
        symbol="BTCUSDT-PERP.BINANCE",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        amount=5,
    )
    assert order.status == OrderStatus.FAILED

async def test_position_update_buy_and_sell(mock_linear_connector: MockLinearConnector):
    await mock_linear_connector._cache._init_storage()
    mock_linear_connector._init_balance()
    mock_linear_connector._init_position()
    order = await mock_linear_connector.create_order(
        symbol="BTCUSDT-PERP.BINANCE",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        amount=Decimal("1"),
    )
    assert order.status == OrderStatus.PENDING
    
    position = mock_linear_connector._cache.get_position("BTCUSDT-PERP.BINANCE").unwrap()
    assert position.amount == Decimal("1")
    assert position.side == PositionSide.LONG
    assert position.entry_price == 10000
    assert position.unrealized_pnl == 0
    assert position.realized_pnl == 0
    assert mock_linear_connector.pnl == 10000 * (1 - mock_linear_connector._fee_rate)
    
    order = await mock_linear_connector.create_order(
        symbol="BTCUSDT-PERP.BINANCE",
        side=OrderSide.SELL,
        type=OrderType.LIMIT,
        amount=Decimal("1"),
    )
    assert order.status == OrderStatus.PENDING
    
    position = mock_linear_connector._cache.get_position("BTCUSDT-PERP.BINANCE").unwrap()
    assert position.amount == Decimal("0")
    assert position.side is None
    assert position.entry_price == 10000
    assert position.unrealized_pnl == 0
    assert position.realized_pnl == 0
    
    assert mock_linear_connector.pnl == 10000 * (1 - 2*mock_linear_connector._fee_rate)

async def test_position_update_sell_and_buy(mock_linear_connector: MockLinearConnector):
    await mock_linear_connector._cache._init_storage()
    mock_linear_connector._init_balance()
    mock_linear_connector._init_position()
    order = await mock_linear_connector.create_order(
        symbol="BTCUSDT-PERP.BINANCE",
        side=OrderSide.SELL,
        type=OrderType.LIMIT,
        amount=Decimal("1"),
    )
    assert order.status == OrderStatus.PENDING
    
    position = mock_linear_connector._cache.get_position("BTCUSDT-PERP.BINANCE").unwrap()
    assert position.amount == Decimal("1")
    assert position.signed_amount == -1
    assert position.side == PositionSide.SHORT
    assert position.entry_price == 10000
    assert position.unrealized_pnl == 0
    assert position.realized_pnl == 0
    assert mock_linear_connector.pnl == 10000 * (1 - mock_linear_connector._fee_rate)
    
    order = await mock_linear_connector.create_order(
        symbol="BTCUSDT-PERP.BINANCE",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        amount=Decimal("1"),
    )
    assert order.status == OrderStatus.PENDING
    
    position = mock_linear_connector._cache.get_position("BTCUSDT-PERP.BINANCE").unwrap()
    assert position.amount == Decimal("0")
    assert position.side is None
    assert position.entry_price == 10000
    assert position.unrealized_pnl == 0
    assert position.realized_pnl == 0
    
    assert mock_linear_connector.pnl == 10000 * (1 - 2*mock_linear_connector._fee_rate)

async def test_position_pnl_update(mock_linear_connector: MockLinearConnector):
    await mock_linear_connector._cache._init_storage()
    mock_linear_connector._init_balance()
    mock_linear_connector._init_position()
    order = await mock_linear_connector.create_order(
        symbol="BTCUSDT-PERP.BINANCE",
        side=OrderSide.SELL,
        type=OrderType.LIMIT,
        amount=Decimal("1"),
    )
    assert order.status == OrderStatus.PENDING
    
    position = mock_linear_connector._cache.get_position("BTCUSDT-PERP.BINANCE").unwrap()
    assert position.amount == Decimal("1")
    assert position.signed_amount == -1
    assert position.side == PositionSide.SHORT
    assert position.entry_price == 10000
    assert position.unrealized_pnl == 0
    assert position.realized_pnl == 0
    fee_1 = float(str(order.fee))
    assert mock_linear_connector.pnl == 10000 - fee_1
    
    order = await mock_linear_connector.create_order(
        symbol="BTCUSDT-PERP.BINANCE",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        amount=Decimal("0.5"),
    )
    assert order.status == OrderStatus.PENDING
    
    position = mock_linear_connector._cache.get_position("BTCUSDT-PERP.BINANCE").unwrap()
    assert position.amount == Decimal("0.5")
    assert position.side == PositionSide.SHORT
    assert position.entry_price == 10000
    assert position.unrealized_pnl == 0
    assert position.realized_pnl == 0
    fee_2 = float(str(order.fee))
    assert mock_linear_connector.pnl == 10000 - fee_1 - fee_2
    
    order = await mock_linear_connector.create_order(
        symbol="BTCUSDT-PERP.BINANCE",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        amount=Decimal("0.5"),
    )
    assert order.status == OrderStatus.PENDING
    
    position = mock_linear_connector._cache.get_position("BTCUSDT-PERP.BINANCE").unwrap()
    assert position.amount == Decimal("0")
    assert position.side is None
    assert position.entry_price == 10000
    assert position.unrealized_pnl == 0
    assert position.realized_pnl == 500 
    fee_3 = float(str(order.fee))
    assert mock_linear_connector.pnl == 10000 + position.realized_pnl - fee_3 - fee_2 - fee_1

async def test_update_unrealized_pnl(mock_linear_connector: MockLinearConnector):
    await mock_linear_connector._cache._init_storage()
    mock_linear_connector._init_balance()
    mock_linear_connector._init_position()
    order = await mock_linear_connector.create_order(
        symbol="BTCUSDT-PERP.BINANCE",
        side=OrderSide.SELL,
        type=OrderType.LIMIT,
        amount=Decimal("1"),
    )
    assert order.status == OrderStatus.PENDING
    
    fee_1 = float(str(order.fee))
    
    # update unrealized pnl
    mock_linear_connector._update_unrealized_pnl()
    assert mock_linear_connector.unrealized_pnl == 0
    
    # update pnl
    mock_linear_connector._update_unrealized_pnl()
    assert mock_linear_connector.unrealized_pnl == -1000
    
    # update pnl
    mock_linear_connector._update_unrealized_pnl()
    assert mock_linear_connector.unrealized_pnl == +1000
    
    mock_linear_connector._update_unrealized_pnl()
    assert mock_linear_connector.unrealized_pnl == 0
    
    
    assert mock_linear_connector.pnl == 10000 - fee_1

async def test_flips_direction(mock_linear_connector: MockLinearConnector):
    await mock_linear_connector._cache._init_storage()
    mock_linear_connector._init_balance()
    mock_linear_connector._init_position()
    
    order = await mock_linear_connector.create_order(
        symbol="BTCUSDT-PERP.BINANCE",
        side=OrderSide.SELL,
        type=OrderType.LIMIT,
        amount=Decimal("1"),
    )
    
    assert order.status == OrderStatus.PENDING
    position = mock_linear_connector._cache.get_position("BTCUSDT-PERP.BINANCE").unwrap()
    assert position.amount == Decimal("1")
    assert position.signed_amount == Decimal("-1")
    assert position.side == PositionSide.SHORT
    assert position.entry_price == 10000
    assert position.unrealized_pnl == 0
    assert position.realized_pnl == 0
    
    order = await mock_linear_connector.create_order(
        symbol="BTCUSDT-PERP.BINANCE",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        amount=Decimal("1.5"),
    )
    
    assert order.status == OrderStatus.PENDING
    position = mock_linear_connector._cache.get_position("BTCUSDT-PERP.BINANCE").unwrap()
    assert position.amount == Decimal("0.5")
    assert position.signed_amount == Decimal("0.5")
    assert position.side == PositionSide.LONG
    assert position.entry_price == 10000
    assert position.unrealized_pnl == 0
    assert position.realized_pnl == 0

    
    