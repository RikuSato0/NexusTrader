import asyncio
import numpy as np
from streamz import Stream
from tradebot.exchange._binance import BinanceWebsocketManager
from tradebot.constants import MARKET_URLS


spot_stream = Stream()
future_stream = Stream()

window_size = 20


def process_trade(msg):
    return float(msg["p"])


def calculate_diff(prices):
    if len(prices) < 2:
        return 0
    return prices[-1] - prices[-2]


def calculate_sum(diffs):
    return sum(diffs)


def cb_future(msg):
    if "e" in msg and msg["e"] == "trade":
        future_stream.emit(process_trade(msg))


def cb_spot(msg):
    if "e" in msg and msg["e"] == "trade":
        spot_stream.emit(process_trade(msg))


async def main():
    try:
        ws_spot_client = BinanceWebsocketManager(
            base_url="wss://stream.binance.com:9443/ws"
        )
        ws_um_client = BinanceWebsocketManager(base_url="wss://fstream.binance.com/ws")
        await ws_um_client.subscribe_trade("BTCUSDT", callback=cb_future)
        await ws_spot_client.subscribe_trade("BTCUSDT", callback=cb_spot)

        # 计算差值
        spot_diff = spot_stream.sliding_window(2).map(calculate_diff)
        future_diff = future_stream.sliding_window(2).map(calculate_diff)

        # 计算滑动窗口的和
        spot_sum = spot_diff.sliding_window(window_size).map(calculate_sum)
        future_sum = future_diff.sliding_window(window_size).map(calculate_sum)

        # 合并spot和future的结果
        combined = spot_sum.combine_latest(future_sum).sink(
            lambda x: print(
                f"Spot: {x[0]:.3f}, Future: {x[1]:.3f}, Sigma: {x[0] + x[1]:.3f}"
            )
        )

        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await ws_spot_client.close()
        await ws_um_client.close()
        print("Websocket closed")


if __name__ == "__main__":
    asyncio.run(main())
