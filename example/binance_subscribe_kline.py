import asyncio
import ccxt

from tradebot.exchange import BinanceWebsocketManager
from tradebot.constants import Url

market_id = {}
    
market = ccxt.binance().load_markets()
for _,v in market.items():
    if v['subType'] == 'linear':
        market_id[f"{v['id']}_swap"] = v
    elif v['type'] == 'spot':
        market_id[f"{v['id']}_spot"] = v
    else:
        market_id[v['id']] = v

def cb_cm_future(msg):
    print(msg)

def cb_um_future(msg):
    print(msg)

def cb_spot(msg):
    print(msg)
    

async def main():
    try:
        ws_spot_client = BinanceWebsocketManager(Url.Binance.Spot)
        ws_um_client = BinanceWebsocketManager(Url.Binance.UsdMFuture)
        ws_cm_client = BinanceWebsocketManager(Url.Binance.CoinMFuture)
        await ws_cm_client.subscribe_kline("BTCUSD_PERP", interval="1m", callback=cb_cm_future)
        await ws_um_client.subscribe_kline("BTCUSDT", interval="1m", callback=cb_um_future)
        await ws_spot_client.subscribe_kline("BTCUSDT", interval='1s' ,callback=cb_spot)
        await ws_spot_client.subscribe_klines(['ETHUSDT', 'SOLOUSDT'], interval='1s', callback=cb_spot)
        
        while True:
            await asyncio.sleep(1)
        
    except asyncio.CancelledError:
        await ws_spot_client.close()
        await ws_um_client.close()
        print("Websocket closed")

if __name__ == "__main__":
    asyncio.run(main())
