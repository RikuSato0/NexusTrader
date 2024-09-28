import ccxt
import pytest
import os

from tradebot.utils import parse_event_data, stream_generator


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
    test_file_path = os.path.join("test", "test_data", "kline.log")
    for event_data in stream_generator(test_file_path):
        symbol = event_data.get("s", None)
        result_spot = parse_event_data(event_data, market_id, "spot")
        if result_spot:
            assert result_spot['s'] == symbol.replace("USDT", "/USDT")
    for event_data in stream_generator(test_file_path):
        symbol = event_data.get("s", None)
        result_swap = parse_event_data(event_data, market_id, "swap")
        if result_swap:
            assert result_swap['s'] == symbol.replace("USDT", "/USDT:USDT")
