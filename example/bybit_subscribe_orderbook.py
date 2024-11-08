import asyncio
import orjson
from tradebot.exchange.bybit import BybitAccountType, BybitWSClient
from tradebot.log import SpdLog

log = SpdLog.get_logger(__name__, level="INFO", flush=False)

def handler(msg):
    try:
        msg = orjson.loads(msg)
        # print(msg)
        log.info(str(msg))
    except orjson.JSONDecodeError:
        pass
        # print(msg)
    

async def main():
    try:
        
        bybit_ws = BybitWSClient(BybitAccountType.LINEAR, handler)
        await bybit_ws.subscribe_order_book("BTCUSDT", 1)
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await bybit_ws.disconnect()
        print("Websocket closed.")

if __name__ == "__main__":
    asyncio.run(main())
