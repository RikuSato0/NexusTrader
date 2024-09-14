import asyncio
import uvloop

from pyinstrument import Profiler


from tradebot.exchange import OkxWebsocketManager
from tradebot.entity import market


def cb(msg):
    if "data" in msg:
        market.update(
            symbol=msg["arg"]["instId"].replace("-", "/"),
            ask=msg["data"][0]["asks"][0][0],
            bid=msg["data"][0]["bids"][0][0],
            ask_vol=msg["data"][0]["asks"][0][1],
            bid_vol=msg["data"][0]["bids"][0][1]
        )
    
    
async def main():
    try:
        okx_ws_manager = OkxWebsocketManager(demo_trade=False)
        await okx_ws_manager.subscribe(symbols=["BTC/USDT"], typ="spot", channel="bbo-tbt", callback=cb) # Subscribe to orderbook
        
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await okx_ws_manager.close()
        print("Websocket closed.")
        return

if __name__ == "__main__":
    profiler = Profiler()
    profiler.start()
    uvloop.run(main())
    profiler.stop()
    profiler.print(show_all=True)
