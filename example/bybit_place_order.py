import asyncio
from decimal import Decimal

from tradebot.constants import CONFIG
from tradebot.constants import OrderSide, OrderType, TimeInForce
from tradebot.exchange.bybit import BybitExchangeManager, BybitPrivateConnector

BYBIT_API_KEY = CONFIG['bybit_testnet_2']['API_KEY']
BYBIT_API_SECRET = CONFIG['bybit_testnet_2']['SECRET']

async def main():
    try:
        config = {
            "apiKey": BYBIT_API_KEY,
            "secret": BYBIT_API_SECRET,
            "sandbox": True,
        }
        exchange = BybitExchangeManager(
            config=config,
        )
        connector = BybitPrivateConnector(exchange, testnet=True, strategy_id="strategy_01", user_id="test_user")
        
        await connector.connect()   
        await asyncio.sleep(10) # wait for the connection to be established
        
        order = await connector.create_order(
            symbol="BTC/USDT:USDT",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            amount=Decimal("0.001"),
            price=Decimal("79811"),
        )
        
        print(order)
        
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("CancelledError")
    finally:
        await connector.disconnect()
if __name__ == "__main__":
    asyncio.run(main())
    


