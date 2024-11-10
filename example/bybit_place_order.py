import asyncio
from tradebot.constants import CONFIG
from tradebot.exchange.bybit import BybitApiClient

BYBIT_API_KEY = CONFIG['bybit_testnet_2']['API_KEY']
BYBIT_API_SECRET = CONFIG['bybit_testnet_2']['SECRET']

async def main():
    api_client = BybitApiClient(
        api_key=BYBIT_API_KEY,
        secret=BYBIT_API_SECRET,
        testnet=True,
    )
    
    try:
        res = await api_client.post_v5_order_create(
            category="linear",
            symbol="BTCUSDT",
            side="Buy",
            order_type="Market",
            qty=0.01,
            positionIdx=1,
        )
        
        print(res)
        
        res = await api_client.post_v5_order_create(
            category="linear",
            symbol="BTCUSDT",
            side="Sell",
            order_type="Market",
            qty=0.01,
            reduceOnly=True,
            positionIdx=1,
        )
        
        print(res)
        
        res = await api_client.post_v5_order_create(
            category="linear",
            symbol="BTCUSDT",
            side="Sell",
            order_type="Limit",
            qty=0.01,
            price="69000",
            timeInForce="GTC",
            positionIdx=2,
        )
        print(res)
        id = res.result.orderId
        
        res = await api_client.post_v5_order_cancel(
            category="linear",
            symbol="BTCUSDT",
            orderId=id,
        )
        print(res)
        
    finally:
        await api_client.close_session()

if __name__ == "__main__":
    asyncio.run(main())
    


