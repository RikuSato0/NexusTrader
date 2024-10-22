import asyncio


from tradebot.exchange._binance import BinanceWebsocketManager
from tradebot.constants import CONFIG, Url

BINANCE_API_KEY = CONFIG["binance_uni"]["API_KEY"]
BINANCE_API_SECRET = CONFIG["binance_uni"]["SECRET"]


def cb(msg):
    print(msg)


async def main():
    try:
        ws_client = BinanceWebsocketManager(
            Url.Binance.PortfolioMargin,
            api_key=BINANCE_API_KEY,
            secret=BINANCE_API_SECRET,
        )
        await ws_client.subscribe_user_data(callback=cb)

        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        await ws_client.close()
        print("Websocket closed")


if __name__ == "__main__":
    asyncio.run(main())
