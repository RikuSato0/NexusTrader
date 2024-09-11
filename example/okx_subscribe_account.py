import asyncio
import uvloop

from tradebot.exchange import OkxWebsocketManager
from tradebot.constants import OKX_API_KEY, OKX_SECRET, OKX_PASSPHRASE
from tradebot.entity import market
from pprint import pprint

def cb(msg):
    if "data" in msg:
        total_eq = msg["data"][0]["totalEq"]
        print(f"Total Equity: {total_eq}")
    
async def main():
    try:
        config = {
            'apiKey': OKX_API_KEY,
            'secret': OKX_SECRET,
            'passphrase': OKX_PASSPHRASE
        }
        
        okx_ws_manager = OkxWebsocketManager(config=config, demo_trade=True)
        await okx_ws_manager.watch_account(callback=cb)
        
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await okx_ws_manager.close()
        print("Websocket closed.")

if __name__ == "__main__":
    uvloop.run(main())
