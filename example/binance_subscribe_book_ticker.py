import asyncio
import uvloop
from tradebot.exchange import BinanceWSManager
from tradebot.constants import Url
from tradebot.log import SpdLog

async def active_disconnect(ws_client: BinanceWSManager):
    while True:
        await asyncio.sleep(3)
        ws_client._transport.disconnect()


async def main():
    try:
        SpdLog.initialize()
        ws_client = BinanceWSManager(Url.Binance.Spot)
        await ws_client.connect()
        await ws_client.subscribe_book_ticker(symbol="BTCUSDT")
        asyncio.create_task(active_disconnect(ws_client))
        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        ws_client.disconnect()
        print("Websocket closed")


if __name__ == "__main__":
    uvloop.run(main())
