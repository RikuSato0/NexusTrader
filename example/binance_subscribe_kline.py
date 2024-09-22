import asyncio


from tradebot.exchange import BinanceWebsocketManager
from tradebot.entity import log_register
from tradebot.constants import MARKET_URLS



def cb_future(msg):
    print(msg)

def cb_spot(msg):
    print(msg)
    

async def main():
    global ratio
    try:
        ws_spot_client = BinanceWebsocketManager(base_url = "wss://stream.binance.com:9443/ws")
        ws_um_client = BinanceWebsocketManager(base_url = "wss://fstream.binance.com/ws")
        await ws_um_client.subscribe_kline("BTCUSDT", interval="1s", callback=cb_future)
        await ws_spot_client.subscribe_kline("BTCUSDT", interval='1s' ,callback=cb_spot)
        
        while True:
            await asyncio.sleep(1)
        
    except asyncio.CancelledError:
        await ws_spot_client.close()
        await ws_um_client.close()
        print("Websocket closed")

if __name__ == "__main__":
    asyncio.run(main())
