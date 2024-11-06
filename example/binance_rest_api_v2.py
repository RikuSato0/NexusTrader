import asyncio
import time
from tradebot.constants import OrderSide, OrderType
from tradebot.constants import CONFIG
from tradebot.exchange.binance import BinanceHttpClient, BinanceApiClient


BINANCE_API_KEY = CONFIG["binance_future_testnet"]["API_KEY"]
BINANCE_API_SECRET = CONFIG["binance_future_testnet"]["SECRET"]

# BINANCE_API_KEY = CONFIG['binance_uni']['API_KEY']
# BINANCE_API_SECRET = CONFIG['binance_uni']['SECRET']

async def main():
    
    http_client = BinanceHttpClient(
        api_key=BINANCE_API_KEY,
        secret=BINANCE_API_SECRET,
        testnet=True,
    )
    
    rest_api = BinanceApiClient(
        api_key=BINANCE_API_KEY,
        secret=BINANCE_API_SECRET,
        testnet=True,
    )
        
    start = int(time.time() * 1000)
    res = await rest_api.post_fapi_v1_order(
        symbol='BTCUSDT',
        type="MARKET",
        
        side="BUY",
        quantity=0.01,
    )
    print(f'{res["updateTime"] - start} ms')
    
    start = int(time.time() * 1000)
    res = await rest_api.post_fapi_v1_order(
        symbol='BTCUSDT',
        type="MARKET",
        side="SELL",
        quantity=0.01,
        reduceOnly=True,
    )
    print(f'{res["updateTime"] - start} ms')
    
    start = int(time.time() * 1000) 
    res = await http_client.post_fapi_v1_order(
        symbol='BTCUSDT',
        type=OrderType.MARKET,
        side=OrderSide.BUY,
        quantity=0.01,
    )    
    print(f'{res["updateTime"] - start} ms')
    
    start = int(time.time() * 1000) 
    res = await http_client.post_fapi_v1_order(
        symbol='BTCUSDT',
        type=OrderType.MARKET,
        side=OrderSide.SELL,
        quantity=0.01,
        reduceOnly=True,
    )    
    print(f'{res["updateTime"] - start} ms')
    
    await rest_api.close_session()

if __name__ == "__main__":
    asyncio.run(main())
