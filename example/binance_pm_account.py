import asyncio
import ccxt.pro as ccxt
import msgspec
from decimal import Decimal
from pprint import pprint
from tradebot.constants import CONFIG
from tradebot.exchange.binance import BinanceExchangeManager

BINANCE_PM_API = CONFIG["binance_uni"]["API_KEY"]
BINANCE_PM_SECRET = CONFIG["binance_uni"]["SECRET"]

class Asset(msgspec.Struct):
    asset: str
    free: Decimal
    borrowed: Decimal

async def main():
    try:
        config = {
            "exchange_id": "binance",
            "apiKey": BINANCE_PM_API,
            "secret": BINANCE_PM_SECRET,
            "enableRateLimit": False,
            "options": {
                "portfolioMargin": True,
            },
        }
        exchange = BinanceExchangeManager(config)
        api: ccxt.binance = exchange.api
        res = await api.papi_get_account()
        pprint(res)
        # for asset in res:
        #     if Decimal(asset['totalWalletBalance']) > 0:
        #         print(asset)
                # a = Asset(
                #     asset=asset['asset'],
                #     free=Decimal(asset['crossMarginAsset']),
                #     borrowed=Decimal(asset['crossMarginBorrowed']),
                # )
                # print("Cross Margin Asset")
                # print(a)
                
                # print("\nUM Asset")
                # a = Asset(
                #     asset=asset['asset'],
                #     free=Decimal(asset['umWalletBalance']),
                #     borrowed=Decimal(0),
                # )
                # print(a)
                
                # print("\nCM Asset")
                # a = Asset(
                #     asset=asset['asset'],
                #     free=Decimal(asset['cmWalletBalance']),
                #     borrowed=Decimal(0),
                # )
                # print(a)
                # print("=====================================")
       
            
        
        
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
