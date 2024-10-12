import asyncio
import uvloop
import orjson
from tradebot.constants import Url
import time
from picows import ws_connect, WSFrame, WSTransport, WSListener, WSMsgType, WSCloseCode
import websockets
import numpy as np

picows = {}
websockets_dict = {}
latency = []

class BinanceListener(WSListener):
    def on_ws_connected(self, transport: WSTransport):
        print("Connected to Binance Websocket.")
    
    def on_ws_disconnected(self, transport: WSTransport):
        print("Disconnected from Binance Websocket.")

    def on_ws_frame(self, transport: WSTransport, frame: WSFrame):
        if frame.msg_type == WSMsgType.PING:
            return
            
        data = orjson.loads(frame.get_payload_as_bytes())
        picows[data.get('t', 'test')] = time.time_ns()
            



class BinanceWebscokets:
    def __init__(self, url: str):
        self.url = url
        self.tasks = []
    
    async def _subscribe(self):
        async with websockets.connect(self.url) as websocket:
            try:
                async for message in websocket:
                    data = orjson.loads(message)
                    websockets_dict[data.get('t', 'test')] = time.time_ns()
            except websockets.ConnectionClosed:
                print("Connection closed.")
    
    async def subscribe(self):
        self.tasks.append(asyncio.create_task(self._subscribe()))
    
    async def close(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        print("All WebSocket connections closed.")

async def main():
    try:
        url = Url.Binance.Spot.STREAM_URL + "/ws/btcusdt@trade"
        ws_client = BinanceWebscokets(url)
        transport = await ws_connect(BinanceListener, url, enable_auto_ping=True, auto_ping_idle_timeout=2, auto_ping_reply_timeout=1)
        await ws_client.subscribe()
        
        while True:
            await asyncio.sleep(1)
        
    except asyncio.CancelledError:
        await transport.di
        await ws_client.close()
        print("Websocket closed.")


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        for k,v in picows.items():
            if k in websockets_dict:
                latency.append(websockets_dict[k] - v)
        
        print(f"Latency: {np.mean(latency)/1e6} ms, std: {np.std(latency)}, 95%: {np.percentile(latency, 95)/1e6} ms, 99%: {np.percentile(latency, 99)/1e6} ms")
        print("KeyboardInterrupt")
