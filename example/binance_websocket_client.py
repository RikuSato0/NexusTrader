import orjson
import asyncio
from nexustrader.exchange.binance import BinanceAccountType
from nexustrader.exchange.binance.websockets import BinanceWSClient


def msg_handler(raw):
    msg = orjson.loads(raw)
    print(msg)

async def main():
    loop = asyncio.get_event_loop()
    client = BinanceWSClient(
        account_type=BinanceAccountType.SPOT,
        handler=msg_handler,
        loop=loop,
    )
    
    await client.connect()
    
    await client.subscribe_book_ticker("BTCUSDT")
    
    await asyncio.sleep(30)
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
