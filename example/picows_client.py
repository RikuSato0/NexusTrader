from picows import WSListener, WSTransport, WSFrame, WSMsgType, ws_connect, WSError
import asyncio
import json
import orjson
import time
from asynciolimiter import Limiter


class WSClient(WSListener):
    def __init__(self, exchange_id: str = ""):
        self._exchange_id = exchange_id
        self.msg_queue = asyncio.Queue()

    def on_ws_connected(self, transport: WSTransport):
        print(f"Connected to {self._exchange_id} Websocket.")

    def on_ws_disconnected(self, transport: WSTransport):
        print(f"Disconnected from {self._exchange_id} Websocket.")

    def on_ws_frame(self, transport: WSTransport, frame: WSFrame):
        if frame.msg_type == WSMsgType.PING:
            transport.send_pong(frame.get_payload_as_bytes())
            return
        try:
            msg = orjson.loads(frame.get_payload_as_bytes())
            self.msg_queue.put_nowait(msg)
        except Exception as e:
            print(frame.get_payload_as_bytes())
            print(f"Error parsing message: {e}")


class BinanceMsgDispatcher:
    def _fund(): ...

    def _trade(): ...


class BinanceWsManager(BinanceMsgDispatcher):
    def __init__(self, url: str):
        self._url = url
        self._ping_idle_timeout = 2
        self._ping_reply_timeout = 1
        self._listener = None
        self._transport = None
        self._subscriptions = {}
        self._limiter = Limiter(5 / 1)  # 5 requests per second

    @property
    def connected(self):
        return self._transport and self._listener

    async def _connect(self):
        WSClientFactory = lambda: WSClient("Binance")  # noqa: E731
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
            asyncio.create_task(self.connection_monitor())

    async def connection_monitor(self):
        while True:
            if not self.connected:
                try:
                    await self._connect()
                    await self._resubscribe()

                # why need to catch `WSError`:
                # ws_connect may throw any exception that asyncio.Loop.create_connection can throw.
                # ws_connect may throw WSError when there is an error during websocket negotiation phase.
                except WSError as e:
                    print(f"Connection error: {e}")
                    # should reconnect
                    self._transport, self._listener = None, None
            else:
                await self._transport.wait_disconnected()
                self._transport, self._listener = None, None

            # TODO: progressively retry
            await asyncio.sleep(0.2)

    async def _handle_connection(self):
        reconnect = False
        while True:
            try:
                await self._connect(reconnect=reconnect)
                await self._resubscribe()
                await self._transport.wait_disconnected()
            except WSError as e:
                print(f"Connection error: {e}")
            reconnect = True
            await asyncio.sleep(1)

    def _send_payload(self, payload: dict):
        self._transport.send(WSMsgType.TEXT, json.dumps(payload).encode("utf-8"))

    async def _resubscribe(self):
        for _, payload in self._subscriptions.items():
            await self._limiter.wait()
            self._send_payload(payload)

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
            self._send_payload(payload)
        else:
            print(f"Already subscribed to {subscription_id}")

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
            self._send_payload(payload)
        else:
            print(f"Already subscribed to {subscription_id}")

    async def _msg_handler(self):
        while True:
            msg = await self._listener.msg_queue.get()
            # TODO: handle different event types of messages
            print(msg)
            self._listener.msg_queue.task_done()

    async def start(self):
        asyncio.create_task(self._msg_handler())
        while True:
            await asyncio.sleep(1)


async def main():
    try:
        url = "wss://stream.binance.com:9443/ws"
        ws_manager = BinanceWsManager(url)
        await ws_manager.connect()
        await ws_manager.subscribe_book_ticker("BTCUSDT")
        await ws_manager.subscribe_book_ticker("ETHUSDT")
        await ws_manager.subscribe_book_ticker("SOLUSDT")
        await ws_manager.subscribe_book_ticker("BNBUSDT")
        await ws_manager.subscribe_trade("BTCUSDT")
        await ws_manager.subscribe_trade("ETHUSDT")
        await ws_manager.subscribe_trade("BNBUSDT")
        await ws_manager.subscribe_trade("SOLUSDT")
        await ws_manager.start()

    except asyncio.CancelledError:
        print("Websocket closed.")


if __name__ == "__main__":
    asyncio.run(main())
