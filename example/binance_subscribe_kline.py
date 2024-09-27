import asyncio


from tradebot.exchange import BinanceWebsocketManager
from tradebot.entity import log_register
from tradebot.constants import Url



def cb_future(msg):
    print(msg)

def cb_spot(msg):
    print(msg)
    

async def main():
    global ratio
    try:
        ws_spot_client = BinanceWebsocketManager(Url.Binance.Spot)
        ws_um_client = BinanceWebsocketManager(Url.Binance.UsdMFuture)
        await ws_um_client.subscribe_kline("BTCUSDT", interval="1s", callback=cb_future)
        await ws_spot_client.subscribe_kline("BTCUSDT", interval='1s' ,callback=cb_spot)
        await ws_spot_client.subscribe_klines(['ETHUSDT', 'SOLOUSDT'], interval='1s', callback=cb_spot)
        
        while True:
            await asyncio.sleep(1)
        
    except asyncio.CancelledError:
        await ws_spot_client.close()
        await ws_um_client.close()
        print("Websocket closed")

if __name__ == "__main__":
    asyncio.run(main())
