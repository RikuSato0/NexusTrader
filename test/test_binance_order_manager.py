import pytest

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from ccxt.base.errors import RequestTimeout
from tradebot.exchange.binance import BinanceOrderManager, BinanceExchangeManager
from tradebot.entity import Order

@pytest.fixture
def mock_exchange():
    exchange = MagicMock(spec=BinanceExchangeManager)
    exchange.config = {'exchange_id': 'binance'}
    exchange.api = AsyncMock()
    return exchange

@pytest.fixture
def order_manager(mock_exchange):
    return BinanceOrderManager(mock_exchange)

@pytest.mark.asyncio
async def test_place_limit_order_success(order_manager, mock_exchange):
    mock_exchange.api.create_order.return_value = {
        'amount': 0.01,
        'average': None,
        'clientOrderId': 'x-xcKtGhcueb4225ab0e04ce908f6c67',
        'cost': 0.0,
        'datetime': '2024-10-03T12:22:12.744Z',
        'fee': None,
        'fees': [],
        'filled': 0.0,
        'id': '4060681953',
        'info': {'avgPrice': '0.00',
                'clientOrderId': 'x-xcKtGhcueb4225ab0e04ce908f6c67',
                'closePosition': False,
                'cumQty': '0.000',
                'cumQuote': '0.00000',
                'executedQty': '0.000',
                'goodTillDate': '0',
                'orderId': '4060681953',
                'origQty': '0.010',
                'origType': 'LIMIT',
                'positionSide': 'LONG',
                'price': '59695.00',
                'priceMatch': 'NONE',
                'priceProtect': False,
                'reduceOnly': False,
                'selfTradePreventionMode': 'NONE',
                'side': 'BUY',
                'status': 'NEW',
                'stopPrice': '0.00',
                'symbol': 'BTCUSDT',
                'timeInForce': 'GTC',
                'type': 'LIMIT',
                'updateTime': '1727958132744',
                'workingType': 'CONTRACT_PRICE'},
                'lastTradeTimestamp': None,
        'lastUpdateTimestamp': 1727958132744,
        'postOnly': False,
        'price': 59695.0,
        'reduceOnly': False,
        'remaining': 0.01,
        'side': 'buy',
        'status': 'open',
        'stopLossPrice': None,
        'stopPrice': None,
        'symbol': 'BTC/USDT:USDT',
        'takeProfitPrice': None,
        'timeInForce': 'GTC',
        'timestamp': 1727958132744,
        'trades': [],
        'triggerPrice': None,
        'type': 'limit'
    }
    result = await order_manager.place_limit_order(
        symbol = "BTC/USDT:USDT",
        side="buy",
        price=59695,
        amount=0.01,
        positionSide="LONG",
    )

    assert isinstance(result, Order)
    assert result.id == '4060681953'
    assert result.symbol == 'BTC/USDT:USDT'
    assert result.type == 'limit'
    assert result.side == 'buy'
    assert result.amount == Decimal('0.01')
    assert result.price == 59695

@pytest.mark.asyncio
async def test_place_limit_order_timeout(order_manager, mock_exchange):
    # 创建一个side_effect函数来控制多次调用的行为
    def side_effect(*args, **kwargs):
        if side_effect.call_count < 2:
            side_effect.call_count += 1
            raise RequestTimeout('Timeout')
        else:
            return {
                'amount': 0.01,
                'average': None,
                'clientOrderId': 'x-xcKtGhcueb4225ab0e04ce908f6c67',
                'cost': 0.0,
                'datetime': '2024-10-03T12:22:12.744Z',
                'fee': None,
                'fees': [],
                'filled': 0.0,
                'id': '4060681953',
                'info': {'avgPrice': '0.00',
                        'clientOrderId': 'x-xcKtGhcueb4225ab0e04ce908f6c67',
                        'closePosition': False,
                        'cumQty': '0.000',
                        'cumQuote': '0.00000',
                        'executedQty': '0.000',
                        'goodTillDate': '0',
                        'orderId': '4060681953',
                        'origQty': '0.010',
                        'origType': 'LIMIT',
                        'positionSide': 'LONG',
                        'price': '59695.00',
                        'priceMatch': 'NONE',
                        'priceProtect': False,
                        'reduceOnly': False,
                        'selfTradePreventionMode': 'NONE',
                        'side': 'BUY',
                        'status': 'NEW',
                        'stopPrice': '0.00',
                        'symbol': 'BTCUSDT',
                        'timeInForce': 'GTC',
                        'type': 'LIMIT',
                        'updateTime': '1727958132744',
                        'workingType': 'CONTRACT_PRICE'},
                'lastTradeTimestamp': None,
                'lastUpdateTimestamp': 1727958132744,
                'postOnly': False,
                'price': 59695.0,
                'reduceOnly': False,
                'remaining': 0.01,
                'side': 'buy',
                'status': 'open',
                'stopLossPrice': None,
                'stopPrice': None,
                'symbol': 'BTC/USDT:USDT',
                'takeProfitPrice': None,
                'timeInForce': 'GTC',
                'timestamp': 1727958132744,
                'trades': [],
                'triggerPrice': None,
                'type': 'limit'
            }
    
    side_effect.call_count = 0
    mock_exchange.api.create_order.side_effect = side_effect

    # 模拟fetch_orders方法
    mock_fetch_orders = AsyncMock()
    mock_fetch_orders.return_value = []
    order_manager.fetch_orders = mock_fetch_orders

    # 移除retry_place_limit_order的模拟，因为我们现在希望它真正被调用

    result = await order_manager.place_limit_order(
        symbol = "BTC/USDT",
        side="buy",
        price=59695.0,
        amount=0.01,
        handle_timeout=True
    )

    assert isinstance(result, Order)
    assert result.success == True
    assert result.status == 'new'
    assert result.id == '4060681953'
    
    # 验证fetch_orders被调用了两次
    assert mock_fetch_orders.call_count == 1
    
    # 验证create_order被调用了三次
    assert mock_exchange.api.create_order.call_count == 3

@pytest.mark.asyncio
async def test_place_market_order_error(order_manager, mock_exchange):
    mock_exchange.api.create_order.side_effect = Exception('binance {"code":-2011,"msg":"Unknown order sent."}')

    result = await order_manager.place_market_order('BTC/USDT', 'sell', Decimal('1.0'))

    assert isinstance(result, Order)
    assert result.success == False

@pytest.mark.asyncio
async def test_cancel_order_success(order_manager, mock_exchange):
    mock_exchange.api.cancel_order.return_value = {
                'amount': 0.01,
                'average': None,
                'clientOrderId': 'x-xcKtGhcuba8376ce65d70c9ac0b389',
                'cost': 0.0,
                'datetime': '2024-10-03T15:39:20.002Z',
                'fee': None,
                'fees': [],
                'filled': 0.0,
                'id': '4060706981',
                'info': {'avgPrice': '0.00',
                        'clientOrderId': 'x-xcKtGhcuba8376ce65d70c9ac0b389',
                        'closePosition': False,
                        'cumQty': '0.000',
                        'cumQuote': '0.00000',
                        'executedQty': '0.000',
                        'goodTillDate': '0',
                        'orderId': '4060706981',
                        'origQty': '0.010',
                        'origType': 'LIMIT',
                        'positionSide': 'LONG',
                        'price': '59695.00',
                        'priceMatch': 'NONE',
                        'priceProtect': False,
                        'reduceOnly': False,
                        'selfTradePreventionMode': 'NONE',
                        'side': 'BUY',
                        'status': 'CANCELED',
                        'stopPrice': '0.00',
                        'symbol': 'BTCUSDT',
                        'timeInForce': 'GTC',
                        'type': 'LIMIT',
                        'updateTime': '1727969960002',
                        'workingType': 'CONTRACT_PRICE'},
                'lastTradeTimestamp': None,
                'lastUpdateTimestamp': 1727969960002,
                'postOnly': False,
                'price': 59695.0,
                'reduceOnly': False,
                'remaining': 0.01,
                'side': 'buy',
                'status': 'canceled',
                'stopLossPrice': None,
                'stopPrice': None,
                'symbol': 'BTC/USDT:USDT',
                'takeProfitPrice': None,
                'timeInForce': 'GTC',
                'timestamp': 1727969960002,
                'trades': [],
                'triggerPrice': None,
                'type': 'limit'
            }

    result = await order_manager.cancel_order('4060706981', 'BTC/USDT"USDT')

    assert isinstance(result, Order)
    assert result.success == True
    assert result.symbol == 'BTC/USDT:USDT'
    assert result.status == 'canceled'
    assert result.id == '4060706981'

@pytest.mark.asyncio
async def test_cancel_order_timeout(order_manager, mock_exchange):
    def side_effect(*args, **kwargs):
        if side_effect.call_count < 2:
            side_effect.call_count += 1
            raise RequestTimeout('Timeout')
        else:
            return {
                'amount': 0.01,
                'average': None,
                'clientOrderId': 'x-xcKtGhcuba8376ce65d70c9ac0b389',
                'cost': 0.0,
                'datetime': '2024-10-03T15:39:20.002Z',
                'fee': None,
                'fees': [],
                'filled': 0.0,
                'id': '4060706981',
                'info': {'avgPrice': '0.00',
                        'clientOrderId': 'x-xcKtGhcuba8376ce65d70c9ac0b389',
                        'closePosition': False,
                        'cumQty': '0.000',
                        'cumQuote': '0.00000',
                        'executedQty': '0.000',
                        'goodTillDate': '0',
                        'orderId': '4060706981',
                        'origQty': '0.010',
                        'origType': 'LIMIT',
                        'positionSide': 'LONG',
                        'price': '59695.00',
                        'priceMatch': 'NONE',
                        'priceProtect': False,
                        'reduceOnly': False,
                        'selfTradePreventionMode': 'NONE',
                        'side': 'BUY',
                        'status': 'CANCELED',
                        'stopPrice': '0.00',
                        'symbol': 'BTCUSDT',
                        'timeInForce': 'GTC',
                        'type': 'LIMIT',
                        'updateTime': '1727969960002',
                        'workingType': 'CONTRACT_PRICE'},
                'lastTradeTimestamp': None,
                'lastUpdateTimestamp': 1727969960002,
                'postOnly': False,
                'price': 59695.0,
                'reduceOnly': False,
                'remaining': 0.01,
                'side': 'buy',
                'status': 'canceled',
                'stopLossPrice': None,
                'stopPrice': None,
                'symbol': 'BTC/USDT:USDT',
                'takeProfitPrice': None,
                'timeInForce': 'GTC',
                'timestamp': 1727969960002,
                'trades': [],
                'triggerPrice': None,
                'type': 'limit'
            }
    side_effect.call_count = 0
    mock_exchange.api.cancel_order.side_effect = side_effect
        
     # 模拟fetch_orders方法
    mock_fetch_orders = AsyncMock()
    mock_fetch_orders.return_value = []
    order_manager.fetch_orders = mock_fetch_orders

    # 移除retry_place_limit_order的模拟，因为我们现在希望它真正被调用

    result = await order_manager.cancel_order(
        id="4060706981",
        symbol = "BTC/USDT:USDT",
    )

    assert isinstance(result, Order)
    assert result.success == True
    assert result.symbol == 'BTC/USDT:USDT'
    assert result.status == 'canceled'
    assert result.id == '4060706981'
    
    # 验证fetch_orders被调用了两次
    assert mock_fetch_orders.call_count == 1
    
    # 验证create_order被调用了三次
    assert mock_exchange.api.cancel_order.call_count == 3
