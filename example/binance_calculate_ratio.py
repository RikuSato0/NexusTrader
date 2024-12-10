import asyncio


from collections import defaultdict

import numpy as np
from streamz import Stream


from tradebot.exchange import BinanceWebsocketManager
from tradebot.core.entity import log_register

# ratio description

# 1. calulate the ratio of future price and spot price
# 2. add ratio to a rolling window of size 20
# 3. calculate the mean of the rolling window

log = log_register.get_logger("BTCUSDT", level="INFO", flush=False)

spot_stream = Stream()
future_stream = Stream()

window_size = 100

orderbook = defaultdict(float)
queue = asyncio.Queue()


def save(ratio):
    if ratio:
        queue.put_nowait(ratio)

def cb_future(msg):
    if "e" in msg:
        future_stream.emit(msg)
    
def cb_spot(msg):
    if "e" in msg:
        spot_stream.emit(msg)
        
def save_spot(msg):
    symbol = msg['s']
    price = float(msg['p'])
    orderbook[symbol] = price
    return msg

def save_future(msg):
    symbol = msg['s'] + ":USDT"
    price = float(msg['p'])
    orderbook[symbol] = price
    return msg
    

async def main():
    global ratio
    try:
        ws_spot_client = BinanceWebsocketManager(base_url = "wss://stream.binance.com:9443/ws")
        ws_um_client = BinanceWebsocketManager(base_url = "wss://fstream.binance.com/ws")
        await ws_um_client.subscribe_trade("BTCUSDT", callback=cb_future)
        await ws_spot_client.subscribe_trade("BTCUSDT", callback=cb_spot)
        ratio = spot_stream.map(save_spot).combine_latest(future_stream.map(save_future)).map(lambda x: float(x[1]['p']) / float(x[0]['p']) - 1)
        ratio.sliding_window(window_size).map(lambda window: np.mean(window)).sink(save) 
        while True:
            ratio = await queue.get()
            if ratio > -0.00035:
                print(f"spot: {orderbook['BTCUSDT']}, future: {orderbook['BTCUSDT:USDT']}, ratio: {ratio}")
            
            
    except asyncio.CancelledError:
        await ws_spot_client.close()
        await ws_um_client.close()
        print("Websocket closed")

if __name__ == "__main__":
    asyncio.run(main())
