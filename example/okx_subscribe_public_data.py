import asyncio
from tradebot.exchange.okx.websockets import OkxWSClient
from tradebot.exchange.okx import OkxExchangeManager, OkxAccountType


async def main():
    try:
        exchange = OkxExchangeManager({"exchange_id": "okx"})
        await exchange.load_markets()
        
        market, market_id = exchange.market, exchange.market_id
        
        ws_manager = OkxWSClient(
            account_type=OkxAccountType.LIVE,
            market=market,
            market_id=market_id,
        )
        
        await ws_manager.connect()
        
        await ws_manager.subscribe_trade(symbol="BTC/USDT:USDT")
        
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await exchange.close()
        await ws_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
