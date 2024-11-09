import asyncio
from tradebot.exchange.bybit import BybitPublicConnector, BybitAccountType, BybitExchangeManager


async def main():
    try:
        exchange = BybitExchangeManager({"exchange_id": "bybit"})
        await exchange.load_markets()
        public_conn = BybitPublicConnector(BybitAccountType.LINEAR, exchange)
        await public_conn.subscribe_bookl1("BTCUSDT")
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await exchange.close()
        await public_conn.disconnect()
        print("Websocket closed.")

if __name__ == "__main__":
    asyncio.run(main())
