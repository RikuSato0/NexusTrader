import time
import asyncio
from pprint import pprint
from tradebot.constants import CONFIG
from tradebot.base import ExchangeManager, OrderManager
from tradebot.exchange import BinanceOrderManager
from tradebot.exceptions import OrderResponseError
import pandas as pd

BINANCE_API_KEY = CONFIG['binance_future_testnet']['API_KEY']
BINANCE_API_SECRET = CONFIG['binance_future_testnet']['SECRET']

# BINANCE_API_KEY = CONFIG['binance_vip']['API_KEY']
# BINANCE_API_SECRET = CONFIG['binance_vip']['SECRET']


async def main():
    try:
        # config = {
        #     'exchange_id': 'binance',
        #     'sandbox': False,
        #     'apiKey': BINANCE_API_KEY,
        #     'secret': BINANCE_API_SECRET, 
        #     'enableRateLimit': False,
        #     'options': {
        #         'portfolioMargin': True,
        #     }
        # }
        
        config = {
            'exchange_id': 'binance',
            'sandbox': True,
            'apiKey': BINANCE_API_KEY,
            'secret': BINANCE_API_SECRET, 
            'enableRateLimit': False,
        }
        
        exchange = ExchangeManager(config)
        await exchange.load_markets()
        order_manager = BinanceOrderManager(exchange)
        
        
        res = await order_manager.place_limit_order(
            symbol='BTC/USDT:USDT',
            side='buy',
            price=59695,
            amount=0.01,
            positionSide='LONG',
            # reduceOnly=True,
        )
        
        pprint(res)
        
        res = await order_manager.cancel_order(
            id = res.id,
            symbol='BTC/USDT:USDT',
        )
        
        pprint(res)
        
        # res = await order_manager.fetch_orders(
        #     symbol="ICP/USDT:USDT",
        # )
        # orders = {}
        
        # for order in res:
        #     datetime = pd.to_datetime(order.timestamp, unit='ms')
        #     orders[datetime] = order
        
        # pprint(orders)
        
        # res = await order_manager.place_market_order(
        #     symbol='STRK/USDT',
        #     side='sell',
        #     amount=774,
        # )
        
        # pprint(res)
        
        # res = await order_manager.place_limit_order(
        #     symbol='USDC/USDT:USDT',
        #     side='buy',
        #     amount=10,
        #     price=0.95,
        #     newClientOrderId='test',
        # )
        
        # pprint(res)
        
        # await asyncio.sleep(1)
        
        # res = await order_manager.cancel_order(
        #     id=res.id,
        #     symbol='USDC/USDT:USDT',
        # )
        
        # pprint(res)
        
    except OrderResponseError as e:
        print(e)
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
    
