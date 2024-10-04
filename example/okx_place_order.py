import asyncio
from pprint import pprint
from tradebot.constants import CONFIG
from tradebot.base import ExchangeManager
from tradebot.exceptions import OrderResponseError
from tradebot.exchange import OkxOrderManager


OKX_API_KEY = CONFIG['okex_demo']['API_KEY']
OKX_SECRET = CONFIG['okex_demo']['SECRET']
OKX_PASSPHRASE = CONFIG['okex_demo']['PASSPHRASE']


async def main():
    try:
        config = {
            'exchange_id': 'okx',
            'sandbox': True,
            'apiKey': OKX_API_KEY,
            'secret': OKX_SECRET,
            'password': OKX_PASSPHRASE,
            'enableRateLimit': False,
            # 'options': {
            #     'portfolioMargin': True,
            # }
        }
        
        exchange = ExchangeManager(config)
        await exchange.load_markets()
        order_manager = OkxOrderManager(exchange)

        res = await order_manager.place_limit_order(
            symbol='BTC/USDT:USDT',
            side='buy',
            amount=0.5,
            price=50000,
            # reduceOnly=True,
        )
        
        pprint(res)
        
        
        res = await order_manager.cancel_order(
            id = res.id,
            symbol='BTC/USDT:USDT',
        )
        
        pprint(res)
        # res = await order_manager.place_market_order(
        #     symbol='USDC/USDT:USDT',
        #     side='sell',
        #     amount=10,
        #     newClientOrderId='test',
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
    
