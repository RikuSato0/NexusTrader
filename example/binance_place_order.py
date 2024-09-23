import asyncio
from pprint import pprint
from tradebot.constants import API_KEY_UNI, API_SECRET_UNI
from tradebot.base import OrderManager, ExchangeManager
from tradebot.exceptions import OrderResponseError


async def main():
    try:
        config = {
            'exchange_id': 'binance',
            'sandbox': False,
            'apiKey': API_KEY_UNI,
            'secret': API_SECRET_UNI, 
            'enableRateLimit': False,
            'options': {
                'portfolioMargin': True,
            }
        }
        
        exchange = ExchangeManager(config)
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
    
