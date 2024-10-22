import asyncio
import uvloop

from pyinstrument import Profiler


from tradebot.exchange._okx import OkxWebsocketManager
from tradebot.constants import Url


def cb(msg):
    print(msg)
    # if "data" in msg:
    #     market.update(
    #         symbol=msg["arg"]["instId"].replace("-", "/"),
    #         ask=msg["data"][0]["asks"][0][0],
    #         bid=msg["data"][0]["bids"][0][0],
    #         ask_vol=msg["data"][0]["asks"][0][1],
    #         bid_vol=msg["data"][0]["bids"][0][1]
    #     )
    
    
async def main():
    try:
        # For Production Trading Url
        # Base url: "wss://ws.okx.com:8443/ws"
        
        # For AWS Trading Url
        # Base url: "wss://wsaws.okx.com:8443/ws"
        
        # For Demo Trading Url
        # Base url: "wss://wspap.okx.com:8443/ws"
        
        okx = OkxWebsocketManager(url=Url.Okx.LIVE)
        await okx.subscribe_order_book("BTC-USDT", channel="bbo-tbt", callback=cb)
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await okx.close()
        print("Websocket closed.")
        return

if __name__ == "__main__":
    uvloop.run(main())
