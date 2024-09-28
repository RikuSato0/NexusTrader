import ccxt
import pytest
import os

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



def test_parse_event_data(market_id):
    test_file_path = os.path.join("test", "test_data", "ACCOUNT_UPDATE.log")
    for event_data in stream_generator(test_file_path):
        positions = event_data['a']['P']
        symbols = [position['s'].replace("USDT", "/USDT:USDT") for position in positions]
        event_data = parse_user_data_stream(event_data, market_id)
        if event_data:
            symbols_check = [position['s'] for position in event_data['a']['P']]
            assert symbols == symbols_check
