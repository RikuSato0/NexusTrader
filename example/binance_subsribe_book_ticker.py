import asyncio


from tradebot.exchange import BinanceWebsocketManager
from tradebot.entity import log_register
from tradebot.constants import MARKET_URLS

log = log_register.get_logger("BTCUSDT", level="INFO", flush=False)



def cb(msg):
    print(msg)
    


async def main():
    try:
        ws_client = BinanceWebsocketManager(base_url = "wss://fstream.binance.com/ws")
        await ws_client.subscribe_book_ticker("BTCUSDT", callback=cb)
        # await ws_client.subscribe_book_ticker("ETHUSDT", callback=cb)
        # await ws_client.subscribe_agg_trades(["BTCUSDT", "ETHUSDT"], callback=cb)
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await ws_client.close()
        print("Websocket closed")

if __name__ == "__main__":
    asyncio.run(main())
