from tradebot.exchange.binance import BinancePublicConnector, BinanceExchangeManager, BinanceAccountType
import asyncio


async def main():
    try:
        config = {
            "exchange_id": "binance"
        }
        
        exchange = BinanceExchangeManager(config=config)
        
        await exchange.load_markets()
        
        public_conn = BinancePublicConnector(account_type=BinanceAccountType.USD_M_FUTURE, exchange=exchange)
        
        await public_conn.subscribe_trade(symbol="BTC/USDT:USDT")
        
        while True:
            await asyncio.sleep(1)
    finally:
        await public_conn.disconnect()
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
