import ccxt
import pytest
import os

from decimal import Decimal

from tradebot.utils import stream_generator
from tradebot.exchange.binance import parse_user_data_stream


@pytest.fixture
def market_id():
    market_id = {}
    market = ccxt.binance().load_markets()
    for _, v in market.items():
        if v['subType'] == 'linear':
            market_id[f"{v['id']}_swap"] = v
        elif v['type'] == 'spot':
            market_id[f"{v['id']}_spot"] = v
        else:
            market_id[v['id']] = v
    return market_id



def test_parse_order_trade_update_data(market_id, capsys):
    test_file_path = os.path.join("test", "test_data", "ORDER_TRADE_UPDATE.log")
    for event_data in stream_generator(test_file_path):
        """
            {
                "e": "ORDER_TRADE_UPDATE", // Event type
                "T": 1727352962757,  // Transaction time
                "E": 1727352962762, // Event time
                "fs": "UM", // Event business unit. 'UM' for USDS-M futures and 'CM' for COIN-M futures
                "o": {
                    "s": "NOTUSDT", // Symbol
                    "c": "c-11WLU7VP1727352880uzcu2rj4ss0i", // Client order ID
                    "S": "SELL", // Side
                    "o": "LIMIT", // Order type
                    "f": "GTC", // Time in force
                    "q": "5488", // Original quantity
                    "p": "0.0084830", // Original price
                    "ap": "0", // Average price
                    "sp": "0", // Ignore
                    "x": "NEW", // Execution type
                    "X": "NEW", // Order status
                    "i": 4968510801, // Order ID
                    "l": "0", // Order last filled quantity
                    "z": "0", // Order filled accumulated quantity
                    "L": "0", // Last filled price
                    "n": "0", // Commission, will not be returned if no commission
                    "N": "USDT", // Commission asset, will not be returned if no commission
                    "T": 1727352962757, // Order trade time
                    "t": 0, // Trade ID
                    "b": "0", // Bids Notional
                    "a": "46.6067521", // Ask Notional
                    "m": false, // Is this trade the maker side?
                    "R": false, // Is this reduce only
                    "ps": "BOTH", // Position side
                    "rp": "0", // Realized profit of the trade
                    "V": "EXPIRE_NONE", // STP mode
                    "pm": "PM_NONE", 
                    "gtd": 0
                }
            }
        """
        
        if event_data.get("e", None) == "ORDER_TRADE_UPDATE":
            id = event_data['o']['i']
            client_order_id=event_data['o']['c']
            timestamp=event_data['T']
            symbol=event_data['o']['s'].replace("USDT", "/USDT:USDT")
            side = event_data['o']['S'].lower()
            price = float(event_data['o']['p'])
            average= float(event_data['o']['ap'])
            last_filled_price=float(event_data['o']['L'])
            amount=Decimal(event_data['o']['q'])
            filled=Decimal(event_data['o']['z'])
            last_filled=Decimal(event_data['o']['l'])
            fee=float(event_data['o']['n'])
            fee_currency=event_data['o']['N']
            last_trade_timestamp=event_data['o']['T']
            reduce_only=event_data['o']['R']
            position_side=event_data['o']['ps'].lower()
            time_in_force=event_data['o']['f']
            status = event_data['o']['X'].lower()
            
            data = parse_user_data_stream(event_data, market_id)
            
            assert data.id == id
            assert data.client_order_id == client_order_id
            assert data.timestamp == timestamp
            assert data.symbol == symbol
            assert data.side == side
            assert data.price == price
            assert data.average == average
            assert data.last_filled_price == last_filled_price
            assert data.amount == amount
            assert data.filled == filled
            assert data.last_filled == last_filled
            assert data.fee == fee
            assert data.fee_currency == fee_currency
            assert data.last_trade_timestamp == last_trade_timestamp
            assert data.reduce_only == reduce_only
            assert data.position_side == position_side
            assert data.time_in_force == time_in_force
            assert data.status == status

            print(f"id: {data.id} type: {data.type} symbol: {data.symbol} cost: {data.cost} status: {data.status}")
    
    captured = capsys.readouterr()
    print("Test output:")
    print(captured.out)


def test_parse_execution_report_data(market_id, capsys):
    test_file_path = os.path.join("test", "test_data", "executionReport.log")
    for event_data in stream_generator(test_file_path):
        """
            {
                "e": "executionReport", // Event type
                "E": 1727353057267, // Event time
                "s": "ORDIUSDT", // Symbol
                "c": "c-11WLU7VP2rj4ss0i", // Client order ID 
                "S": "BUY", // Side
                "o": "MARKET", // Order type
                "f": "GTC", // Time in force
                "q": "0.50000000", // Order quantity
                "p": "0.00000000", // Order price
                "P": "0.00000000", // Stop price
                "g": -1, // Order list id
                "x": "TRADE", // Execution type
                "X": "PARTIALLY_FILLED", // Order status
                "i": 2233880350, // Order ID
                "l": "0.17000000", // last executed quantity
                "z": "0.17000000", // Cumulative filled quantity
                "L": "36.88000000", // Last executed price
                "n": "0.00000216", // Commission amount
                "N": "BNB", // Commission asset
                "T": 1727353057266, // Transaction time
                "t": 105069149, // Trade ID
                "w": false, // Is the order on the book?
                "m": false, // Is this trade the maker side?
                "O": 1727353057266, // Order creation time
                "Z": "6.26960000", // Cumulative quote asset transacted quantity
                "Y": "6.26960000", // Last quote asset transacted quantity (i.e. lastPrice * lastQty)
                "V": "EXPIRE_MAKER", // Self trade prevention Mode
                "I": 1495839281094 // Ignore
            }
        """
        
        if event_data.get("e", None) == "executionReport":
            id = event_data['i']
            client_order_id=event_data['c']
            timestamp=event_data['T']
            symbol=event_data['s'].replace("USDT", "/USDT")
            side = event_data['S'].lower()
            price = float(event_data['p'])
            last_filled_price=float(event_data['L'])
            amount=Decimal(event_data['q'])
            filled=Decimal(event_data['z'])
            last_filled=Decimal(event_data['l'])
            fee=float(event_data['n'])
            fee_currency=event_data.get('N', None)
            last_trade_timestamp=event_data['T']
            time_in_force=event_data['f']
            status = event_data['X'].lower()
            
            data = parse_user_data_stream(event_data, market_id)
            
            assert data.id == id
            assert data.client_order_id == client_order_id
            assert data.timestamp == timestamp
            assert data.symbol == symbol
            assert data.side == side
            assert data.price == price
            assert data.last_filled_price == last_filled_price
            assert data.amount == amount
            assert data.filled == filled
            assert data.last_filled == last_filled
            assert data.fee == fee
            assert data.fee_currency == fee_currency
            assert data.last_trade_timestamp == last_trade_timestamp
            assert data.time_in_force == time_in_force
            assert data.status == status

            print(f"id: {data.id} type: {data.type} symbol: {data.symbol} cost: {data.cost} status: {data.status}")
    
    captured = capsys.readouterr()
    print("Test output:")
    print(captured.out)
