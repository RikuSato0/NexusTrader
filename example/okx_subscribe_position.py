import asyncio
import uvloop


from pprint import pprint


from tradebot.exchange import OkxWebsocketManager
from tradebot.constants import CONFIG, Url

OKX_API_KEY = CONFIG['okex_demo']['API_KEY']
OKX_SECRET = CONFIG['okex_demo']['SECRET']
OKX_PASSPHRASE = CONFIG['okex_demo']['PASSPHRASE']
OKX_USER = CONFIG['okex_demo']['USER']


def cb(msg):
    print(msg)
    
async def main():
    try:        
        okx_ws_manager = OkxWebsocketManager(url=Url.Okx.DEMO, api_key=OKX_API_KEY, secret=OKX_SECRET, passphrase=OKX_PASSPHRASE)
        await okx_ws_manager.subscribe_positions(callback=cb)
        
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await okx_ws_manager.close()
        print("Websocket closed.")

if __name__ == "__main__":
    uvloop.run(main())
