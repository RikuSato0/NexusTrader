import asyncio
import ccxt.pro as ccxt
import msgspec
from decimal import Decimal
from nexustrader.schema import Asset
from nexustrader.constants import KEYS
from nexustrader.exchange.binance import BinanceExchangeManager

BINANCE_PM_API = KEYS["binance_uni"]["API_KEY"]
BINANCE_PM_SECRET = KEYS["binance_uni"]["SECRET"]


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

        res = await api.papi_get_balance()
        for asset in res:
            if Decimal(asset["totalWalletBalance"]) > 0:
                print(asset)
                a = Asset(
                    asset=asset["asset"],
                    free=Decimal(asset["crossMarginFree"]),
                    borrowed=Decimal(asset["crossMarginBorrowed"]),
                    locked=Decimal(asset["crossMarginLocked"]),
                )
                print("Cross Margin Asset")
                print(a)
                print("Total: ", a.total)
                json_format = msgspec.json.encode(a)
                print(json_format)
                decode = msgspec.json.decode(json_format, type=Asset)
                print(decode)

                print("\nUM Asset")
                a = Asset(
                    asset=asset["asset"],
                    free=Decimal(asset["umWalletBalance"]),
                    borrowed=Decimal(0),
                )
                print(a)

                print("\nCM Asset")
                a = Asset(
                    asset=asset["asset"],
                    free=Decimal(asset["cmWalletBalance"]),
                    borrowed=Decimal(0),
                )
                print(a)
                print("=====================================")

    finally:
        await exchange.close()


if __name__ == "__main__":
    asyncio.run(main())
