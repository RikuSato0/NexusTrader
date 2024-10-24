import asyncio


from tradebot.exchange.binance import BinancePrivateConnector, BinanceExchangeManager, BinanceAccountType
from tradebot.constants import CONFIG

BINANCE_API_KEY = CONFIG["binance_future_testnet"]["API_KEY"]
BINANCE_API_SECRET = CONFIG["binance_future_testnet"]["SECRET"]



async def main():
    try:
    
        exchange = BinanceExchangeManager({"exchange_id": "binance"})
        await exchange.load_markets()
        
        private_conn = BinancePrivateConnector(
            BinanceAccountType.USD_M_FUTURE_TESTNET,
            BINANCE_API_KEY,
            BINANCE_API_SECRET,
            exchange.market,
            exchange.market_id,
        )
        
        await private_conn.connect()
        
        while True:
            await asyncio.sleep(1)
        

    except asyncio.CancelledError:
        print("Websocket closed")
    finally:
        await exchange.close()
        await private_conn.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
