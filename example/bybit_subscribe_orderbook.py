import asyncio


from tradebot.exchange.bybit import BybitWebsocketManager
from tradebot.constants import Url

def cb(msg):
    print(msg)
    

async def main():
    try:
        bybit_ws_manager = BybitWebsocketManager(url=Url.Bybit.Spot, testnet=False)
        await bybit_ws_manager.subscribe_orderbook(symbol="BTCUSDT", depth=1, callback=cb)
        
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await bybit_ws_manager.close()
        print("Websocket closed.")

if __name__ == "__main__":
    asyncio.run(main())
