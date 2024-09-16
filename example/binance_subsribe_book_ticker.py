import asyncio


from tradebot.exchange import BinanceWebsocketManager




def cb(msg):
    print(msg)


async def main():
    try:
        ws_client = BinanceWebsocketManager(base_url = "wss://stream.binance.com:9443/ws")
        await ws_client.subscribe_book_ticker("BTCUSDT", callback=cb)
        await ws_client.subscribe_book_ticker("ETHUSDT", callback=cb)
        await ws_client.subscribe_agg_trades(["BTCUSDT", "ETHUSDT"], callback=cb)
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await ws_client.close()
        print("Websocket closed")

if __name__ == "__main__":
    asyncio.run(main())
