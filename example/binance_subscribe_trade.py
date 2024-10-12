import asyncio
import uvloop
import ccxt
import time
from tradebot.exchange import BinanceWebsocketManager
from tradebot.constants import Url

def cb_spot(msg):
    msg['local'] = int(time.time() * 1e9)
    print(msg)
    

async def main():
    try:
        ws_spot_client = BinanceWebsocketManager(Url.Binance.Spot)
        await ws_spot_client.subscribe_trade("BTCUSDT", callback=cb_spot)
        
        while True:
            await asyncio.sleep(1)
        
    except asyncio.CancelledError:
        await ws_spot_client.close()
        print("Websocket closed")

if __name__ == "__main__":
    uvloop.run(main())
