import asyncio
from tradebot.exchange.binance import BinanceAccountType
from tradebot.exchange.binance.websockets import BinanceWSClient


def ws_handler(data):
    print(data)


async def main():
    try:
        ws = BinanceWSClient(
            account_type=BinanceAccountType.SPOT,
            handler=ws_handler
        )
        
        await ws.subscribe_kline("BTCUSDT", "1m")
        
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        ws.disconnect
        print("Closed")

if __name__ == "__main__":
    asyncio.run(main())
    