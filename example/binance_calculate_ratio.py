import asyncio
import numpy as np
from streamz import Stream
from tradebot.exchange import BinanceWebsocketManager
from tradebot.entity import log_register
from tradebot.constants import MARKET_URLS

log = log_register.get_logger("BTCUSDT", level="INFO", flush=False)

spot_stream = Stream()
future_stream = Stream()

window_size = 20

ratio = spot_stream.combine_latest(future_stream).map(lambda x: float(x[1]['p']) / float(x[0]['p']) - 1)

# print moving average of window_size 20
mean = ratio.sliding_window(window_size).map(lambda window: np.median(window)).sink(print) 


def cb_future(msg):
    if "e" in msg:
        future_stream.emit(msg)
    
def cb_spot(msg):
    if "e" in msg:
        spot_stream.emit(msg)

async def main():
    try:
        ws_spot_client = BinanceWebsocketManager(base_url = "wss://stream.binance.com:9443/ws")
        ws_um_client = BinanceWebsocketManager(base_url = "wss://fstream.binance.com/ws")
        await ws_um_client.subscribe_trade("BTCUSDT", callback=cb_future)
        await ws_spot_client.subscribe_trade("BTCUSDT", callback=cb_spot)
        # await ws_client.subscribe_book_ticker("ETHUSDT", callback=cb)
        # await ws_client.subscribe_agg_trades(["BTCUSDT", "ETHUSDT"], callback=cb)
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await ws_spot_client.close()
        await ws_um_client.close()
        print("Websocket closed")

if __name__ == "__main__":
    asyncio.run(main())
