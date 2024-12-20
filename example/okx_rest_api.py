import asyncio
import time
from tradebot.constants import KEYS
from tradebot.exchange.okx.rest_api import OkxApiClient
from tradebot.exchange.okx.constants import OkxAccountType
OKX_API_KEY = KEYS["okex_demo"]["API_KEY"]
OKX_API_SECRET = KEYS["okex_demo"]["SECRET"]
OKX_PASSPHRASE = KEYS["okex_demo"]["PASSPHRASE"]

async def main():
    rest_api = OkxApiClient(
        api_key=OKX_API_KEY,
        secret=OKX_API_SECRET,
        passphrase=OKX_PASSPHRASE,
        account_type=OkxAccountType.DEMO,
    )
    
    res = await rest_api.post_v5_order_create(
        instId='BTC-USDT-SWAP',
        tdMode='cross',
        side='buy',
        ordType='market',
        sz='0.1',
    )
    print(res)
    
    await rest_api.close_session()

if __name__ == "__main__":
    asyncio.run(main())
