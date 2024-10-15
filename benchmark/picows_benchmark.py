from picows import WSListener, WSTransport, WSFrame, WSMsgType, ws_connect
import asyncio
import orjson
import time
from asynciolimiter import Limiter
from tradebot.log import SpdLog
from collections import defaultdict
import numpy as np




LATENCY = defaultdict(list)


class WSClient(WSListener):
    def __init__(self, exchange_id: str = "", logger = None):
        self._exchange_id = exchange_id
        self.msg_queue = asyncio.Queue()
        self._log = logger
        
    def on_ws_connected(self, transport: WSTransport):
        self._log.info(f"Connected to {self._exchange_id} Websocket.")

    def on_ws_disconnected(self, transport: WSTransport):
        self._log.info(f"Disconnected from {self._exchange_id} Websocket.")

    def on_ws_frame(self, transport: WSTransport, frame: WSFrame):
        if frame.msg_type == WSMsgType.PING:
            transport.send_pong(frame.get_payload_as_bytes())
            return
        try:
            msg = orjson.loads(frame.get_payload_as_bytes())
            self.msg_queue.put_nowait(msg)
        except Exception as e:
            self._log.error(frame.get_payload_as_bytes())
            self._log.error(f"Error parsing message: {e}")


class BinanceMsgDispatcher:
    def _fund(): ...

    def _trade(): ...


class BinanceWsManager(BinanceMsgDispatcher):
    def __init__(self, url: str):
        self._url = url
        self._reconnect_interval = 0.2  # Reconnection interval in seconds
        self._ping_idle_timeout = 2
        self._ping_reply_timeout = 1
        self._listener = None
        self._transport = None
        self._subscriptions = {}
        self._limiter = Limiter(3 / 1)  # 3 requests per second
        self._log = SpdLog.get_logger(type(self).__name__, level="INFO", flush=True)

    @property
    def connected(self):
        return self._transport and self._listener

    async def _connect(self):
        WSClientFactory = lambda: WSClient("Binance", self._log)  # noqa: E731
        self._transport, self._listener = await ws_connect(
            WSClientFactory,
            self._url,
            enable_auto_ping=True,
            auto_ping_idle_timeout=self._ping_idle_timeout,
            auto_ping_reply_timeout=self._ping_reply_timeout,
        )

    async def connect(self):
        if not self.connected:
            await self._connect()
            asyncio.create_task(self._connection_handler())

    async def _connection_handler(self):
        while True:
            try:
                if not self.connected:
                    await self._connect()
                    await self._resubscribe()
                else:
                    await self._transport.wait_disconnected()
            except Exception as e:
                self._log.error(f"Connection error: {e}")
            finally:
                self._transport, self._listener = None, None
                await asyncio.sleep(self._reconnect_interval)

    def _send(self, payload: dict):
        self._transport.send(WSMsgType.TEXT, orjson.dumps(payload))

    async def _resubscribe(self):
        for _, payload in self._subscriptions.items():
            await self._limiter.wait()
            self._send(payload)

    async def subscribe_book_ticker(self, symbol):
        subscription_id = f"book_ticker.{symbol}"
        if subscription_id not in self._subscriptions:
            await self._limiter.wait()
            id = int(time.time() * 1000)
            payload = {
                "method": "SUBSCRIBE",
                "params": [f"{symbol.lower()}@bookTicker"],
                "id": id,
            }
            self._subscriptions[subscription_id] = payload
            self._send(payload)
        else:
            self._log.info(f"Already subscribed to {subscription_id}")

    async def subscribe_trade(self, symbol):
        subscription_id = f"trade.{symbol}"
        if subscription_id not in self._subscriptions:
            await self._limiter.wait()
            id = int(time.time() * 1000)
            payload = {
                "method": "SUBSCRIBE",
                "params": [f"{symbol.lower()}@trade"],
                "id": id,
            }
            self._subscriptions[subscription_id] = payload
            self._send(payload)
        else:
            self._log.info(f"Already subscribed to {subscription_id}")

    def callback(self, msg):
        self._log.info(str(msg))
        # if "E" in msg:
        #     # print(msg)
        #     local = int(time.time() * 1000)
        #     latency = local - msg["E"]
        #     LATENCY[msg["s"]].append(latency)

    async def _msg_handler(self):
        while True:
            msg = await self._listener.msg_queue.get()
            # TODO: handle different event types of messages
            self.callback(msg)
            self._listener.msg_queue.task_done()
    
    def disconnect(self):
        if self.connected:
            self._transport.disconnect()


async def main():
    try:
        SpdLog.initialize()
        url = "wss://stream.binance.com:9443/ws"
        ws_manager = BinanceWsManager(url)
        await ws_manager.connect()
        asyncio.create_task(ws_manager._msg_handler())

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
            # await ws_manager.subscribe_book_ticker(symbol)
            # print(symbol)
            await ws_manager.subscribe_trade(symbol)

        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        ws_manager.disconnect()
        print("Websocket closed.")

    # finally:
    #     for symbol, latencies in LATENCY.items():
    #         avg_latency = np.mean(latencies)
    #         print(
    #             f"Symbol: {symbol}, Avg: {avg_latency:.2f} ms, Median: {np.median(latencies):.2f} ms, Std: {np.std(latencies):.2f} ms 95%: {np.percentile(latencies, 95):.2f} ms, 99%: {np.percentile(latencies, 99):.2f} ms min: {np.min(latencies):.2f} ms max: {np.max(latencies):.2f} ms"
    #         )


if __name__ == "__main__":
    asyncio.run(main())
