import websockets
import json
import asyncio
from asynciolimiter import Limiter
from collections import defaultdict
import time
import orjson
import numpy as np


LATENCY = defaultdict(list)


class WebsocketClient:
    def __init__(self, url: str):
        self.uri = url
        self.ws = None
        self.limiter = Limiter(3 / 1)

    async def connect(self):
        self.ws = await websockets.connect(self.uri)

    async def close(self):
        await self.ws.close()

    async def send(self, payload: str):
        payload = json.dumps(payload)
        await self.ws.send(payload)

    async def recv(self):
        return await self.ws.recv()

    async def listen(self):
        while True:
            try:
                msg = await self.recv()
                msg = orjson.loads(msg)
                if "e" in msg:
                    local = int(time.time() * 1000)
                    LATENCY[msg["s"]].append(local - msg["E"])
            except websockets.exceptions.ConnectionClosedOK:
                print("Connection closed")
                break
            except Exception as e:
                print(e)

    async def subscribe_trade(self, symbol: str):
        await self.limiter.wait()
        print(f"Subscribing to {symbol}")
        payload = {
            "method": "SUBSCRIBE",
            "params": [f"{symbol.lower()}@trade"],
            "id": 1,
        }
        await self.send(payload)


async def main():
    try:
        url = "wss://stream.binance.com:9443/ws"
        ws = WebsocketClient(url)
        await ws.connect()
        asyncio.create_task(ws.listen())
        symbols = [
            "ARKMUSDT",
            "ZECUSDT",
            "MANTAUSDT",
            "ENAUSDT",
            "ARKUSDT",
            "RIFUSDT",
            "BEAMXUSDT",
            "METISUSDT",
            "1000SATSUSDT",
            "AMBUSDT",
            "CHZUSDT",
            "RENUSDT",
            "BANANAUSDT",
            "TAOUSDT",
            "RAREUSDT",
            "SXPUSDT",
            "IDUSDT",
            "LQTYUSDT",
            "RPLUSDT",
            "COMBOUSDT",
            "SEIUSDT",
            "RDNTUSDT",
            "BNXUSDT",
            "NKNUSDT",
            "BNBUSDT",
            "APTUSDT",
            "OXTUSDT",
            "LEVERUSDT",
            "AIUSDT",
            "OMNIUSDT",
            "KDAUSDT",
            "ALPACAUSDT",
            "STRKUSDT",
            "FETUSDT",
            "FIDAUSDT",
            "MKRUSDT",
            "GMTUSDT",
            "VIDTUSDT",
            "UMAUSDT",
            "RONINUSDT",
            "FIOUSDT",
            "BALUSDT",
            "IOUSDT",
            "LDOUSDT",
            "KSMUSDT",
            "TURBOUSDT",
            "GUSDT",
            "POLUSDT",
            "XVSUSDT",
            "SUNUSDT",
            "TIAUSDT",
            "LRCUSDT",
            "1MBABYDOGEUSDT",
            "ZKUSDT",
            "ZENUSDT",
            "HOTUSDT",
            "DARUSDT",
            "AXSUSDT",
            "TRXUSDT",
            "LOKAUSDT",
            "LSKUSDT",
            "GLMUSDT",
            "ETHFIUSDT",
            "ONTUSDT",
            "ONGUSDT",
            "CATIUSDT",
            "REZUSDT",
            "NEIROUSDT",
            "VANRYUSDT",
            "ANKRUSDT",
            "ALPHAUSDT",
        ]

        for symbol in symbols:
            await ws.subscribe_trade(symbol)

        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        print("Cancelled")
    finally:
        await ws.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)
    finally:
        for symbol, latencies in LATENCY.items():
            avg_latency = np.mean(latencies)
            print(
                f"Symbol: {symbol}, Avg: {avg_latency:.2f} ms, Median: {np.median(latencies):.2f} ms, Std: {np.std(latencies):.2f} ms 95%: {np.percentile(latencies, 95):.2f} ms, 99%: {np.percentile(latencies, 99):.2f} ms min: {np.min(latencies):.2f} ms max: {np.max(latencies):.2f} ms"
            )
