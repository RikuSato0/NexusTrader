import asyncio
import orjson
import json
import os
from nexustrader.exchange.bybit import BybitAccountType, BybitWSClient
from nexustrader.core.log import SpdLog

log = SpdLog.get_logger(__name__, level="INFO", flush=False)

data_ws = []
def handler(msg):
    try:
        msg = orjson.loads(msg)
        # data_ws.append(msg)
        # print(msg)
        # log.info(str(msg))
    except orjson.JSONDecodeError:
        pass
        # print(msg)
    

async def main():
    try:
        
        bybit_ws = BybitWSClient(BybitAccountType.LINEAR, handler)
        await bybit_ws.subscribe_kline("BTCUSDT", 1)
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await bybit_ws.disconnect()
        print("Websocket closed.")
    finally:
        file_path = os.path.join('test', 'test_data', 'data_ws.json')
        with open(file_path, 'w') as f:
            json.dump(data_ws, f, indent=4)
        

if __name__ == "__main__":
    asyncio.run(main())
