import os
import json
import msgspec
import orjson
from collections import defaultdict
from tradebot.exchange.bybit.types import BybitWsOrderbookDepthMsg, BybitOrderBook, BybitWsMessageGeneral


file_path = os.path.join('test', 'test_data', 'data_ws.json')

ws_msg_general_decoder = msgspec.json.Decoder(BybitWsMessageGeneral)
ws_msg_orderbook_decoder = msgspec.json.Decoder(BybitWsOrderbookDepthMsg)

orderbooks = defaultdict(BybitOrderBook)

def ws_msg_handler(raw: bytes):
    try:
        ws_msg: BybitWsMessageGeneral = ws_msg_general_decoder.decode(raw)
        if "orderbook" in ws_msg.topic:
            handle_orderbook(raw, ws_msg.topic)
    except Exception as e:
        print(f"Error decoding message: {str(raw)} {e}")
        
def handle_orderbook(raw: bytes, topic: str):
    level = 1
    msg: BybitWsOrderbookDepthMsg = ws_msg_orderbook_decoder.decode(raw)
    id = msg.data.s
        
    orderbook = orderbooks[id]
    res = orderbook.parse_orderbook_depth(msg, levels=level)
    assert res is not None
    assert len(res['bids']) == level 
    assert len(res['asks']) == level 


def stream_generator(file_path: str):
    
    with open(file_path, 'r') as f:
        data_ws = json.load(f)
    
    for data in data_ws:
        yield orjson.dumps(data)


if __name__ == '__main__':
    for raw in stream_generator(file_path):
        ws_msg_handler(raw)
    
