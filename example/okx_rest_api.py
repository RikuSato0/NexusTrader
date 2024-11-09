import asyncio
import time
from tradebot.constants import CONFIG
from tradebot.exchange.okx.rest_api import OkxApiClient

OKX_API_KEY = CONFIG["okex_demo"]["API_KEY"]
OKX_API_SECRET = CONFIG["okex_demo"]["SECRET"]
OKX_PASSPHRASE = CONFIG["okex_demo"]["PASSPHRASE"]

async def main():
    rest_api = OkxApiClient(
        api_key=OKX_API_KEY,
        secret=OKX_API_SECRET,
        passphrase=OKX_PASSPHRASE,
        testnet=True,
    )
    
    start = int(time.time() * 1000)
    res = await rest_api.place_order(
        instId='BTC-USDT-SWAP',
        tdMode='cross',
        side='buy',
        ordType='market',
        sz='0.01'
    )
    print(res)
    
    start = int(time.time() * 1000)
    res = await rest_api.place_order(
        instId='BTC-USDT-SWAP',
        tdMode='cross',
        side='sell',
        ordType='market',
        sz='0.01',
        reduceOnly=True
    )
    print(res)
    
    await rest_api.close_session()

if __name__ == "__main__":
    asyncio.run(main())