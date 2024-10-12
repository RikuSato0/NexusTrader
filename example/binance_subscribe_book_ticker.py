import asyncio
import uvloop
from tradebot.exchange import BinanceWebsocketManager
from tradebot.constants import Url


def cb_spot(msg):
    print(msg)


async def main():
    try:
        ws_spot_client = BinanceWebsocketManager(Url.Binance.Spot)
        await ws_spot_client.subscribe_book_ticker_v2(
            symbol="BTCUSDT", callback=cb_spot
        )
        await ws_spot_client.subscribe_book_ticker_v2(
            symbol="ETHUSDT", callback=cb_spot
        )
        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        await ws_spot_client.close()
        print("Websocket closed")


if __name__ == "__main__":
    uvloop.run(main())
