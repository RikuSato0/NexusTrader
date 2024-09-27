import asyncio
from pprint import pprint
from tradebot.constants import CONFIG
from tradebot.base import OrderManager, ExchangeManager
from tradebot.exceptions import OrderResponseError


BINANCE_API_KEY = CONFIG['binance_uni']['API_KEY']
BINANCE_API_SECRET = CONFIG['binance_uni']['SECRET']


async def main():
    try:
        config = {
            'exchange_id': 'binance',
            'sandbox': False,
            'apiKey': BINANCE_API_KEY,
            'secret': BINANCE_API_SECRET, 
            'enableRateLimit': False,
            'options': {
                'portfolioMargin': True,
            }
        }
        
        exchange = ExchangeManager(config)
        await exchange.load_markets()
        order_manager = OrderManager(exchange)

        res = await order_manager.place_market_order(
            symbol='USDC/USDT',
            side='buy',
            amount=10,
            newClientOrderId='test',
        )
        
        pprint(res)
        
        res = await order_manager.place_market_order(
            symbol='USDC/USDT',
            side='sell',
            amount=10,
            newClientOrderId='test',
        )
        
        pprint(res)
        
        res = await order_manager.place_limit_order(
            symbol='USDC/USDT',
            side='buy',
            amount=10,
            price=0.95,
            newClientOrderId='test',
        )
        
        pprint(res)
        
        await asyncio.sleep(1)
        
        res = await order_manager.cancel_order(
            id=res.id,
            symbol='USDC/USDT',
        )
        
        pprint(res)
        
    except OrderResponseError as e:
        print(e)
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
    
