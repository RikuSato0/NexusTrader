import asyncio


from tradebot.exchange import BinanceWebsocketManager
from tradebot.constants import API_KEY_UNI, API_SECRET_UNI



def cb(msg):
    print(msg)
    

async def main():
    try:
        ws_client = BinanceWebsocketManager(base_url="wss://fstream.binance.com/pm/ws", api_key=API_KEY_UNI, secret=API_SECRET_UNI)
        await ws_client.subscribe_user_data('portfolio', callback=cb)
        
        while True:
            await asyncio.sleep(1)
        
    except asyncio.CancelledError:
        await ws_client.close()
        print("Websocket closed")

if __name__ == "__main__":
    asyncio.run(main())
