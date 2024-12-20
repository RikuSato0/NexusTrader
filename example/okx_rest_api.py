import asyncio
from tradebot.constants import KEYS
from tradebot.exchange.okx.rest_api import OkxApiClient

OKX_API_KEY = KEYS["okex_demo"]["API_KEY"]
OKX_API_SECRET = KEYS["okex_demo"]["SECRET"]
OKX_PASSPHRASE = KEYS["okex_demo"]["PASSPHRASE"]

async def main():
    try:
        rest_api = OkxApiClient(
            api_key=OKX_API_KEY,
            secret=OKX_API_SECRET,
            passphrase=OKX_PASSPHRASE,
            testnet=True,
        )
        
        res = await rest_api.post_api_v5_trade_order(
            instId='BTC-USDT-SWAP',
            tdMode='cross',
            side='buy',
            ordType='market',
            sz='0.1',
            posSide='long',
        )
        print(res)
    except Exception as e:
        print(e)
    finally:
        await rest_api.close_session()

if __name__ == "__main__":
    asyncio.run(main())

