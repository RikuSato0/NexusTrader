import asyncio
import uvloop


from tradebot.entity import redis_pool
from tradebot.entity import Context
from tradebot.exchange import OkxWebsocketManager
from tradebot.constants import OKX_API_KEY, OKX_SECRET, OKX_PASSPHRASE, OKX_USER

rc = redis_pool.get_client()
rc.flushall()
context = Context(redis_client=rc, user=OKX_USER)

def cb(msg):
    if "data" in msg:
        for asset in msg["data"][0]["details"]:
            context.portfolio_account[asset["ccy"]] = float(asset["availEq"])
            print(f"{asset['ccy']}: {asset['availEq']}")
        print("--------------------")
    
async def main():
    try:
        okx_ws_manager = OkxWebsocketManager(
            base_url="wss://wspap.okx.com:8443/ws",
            api_key=OKX_API_KEY,
            secret=OKX_SECRET,
            passphrase=OKX_PASSPHRASE,
        )
        await okx_ws_manager.subscribe_account(callback=cb)
        
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        redis_pool.close()
        await okx_ws_manager.close()
        print("Websocket closed.")

if __name__ == "__main__":
    uvloop.run(main())
