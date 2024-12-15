import zmq.asyncio
import orjson
import asyncio
from typing import Dict, Callable
from tradebot.exchange.bybit.schema import BybitMarket
from tradebot.exchange.bybit import BybitExchangeManager
from decimal import Decimal
from tradebot.config import ZeroMQSignalConfig

class BybitSignal:
    def __init__(self, market: Dict[str, BybitMarket] = None):
        context = zmq.asyncio.Context()
        self.socket = context.socket(zmq.SUB)
        self.socket.connect("ipc:///tmp/zmq_data")
        self.socket.setsockopt(zmq.SUBSCRIBE, b"")
        self.market = market

    async def receive(self):
        while True:
            pos = {}
            response = await self.socket.recv()
            data = orjson.loads(response)
            for d in data:
                try:
                    symbol: str = d["instrumentID"]
                    symbol = symbol.replace("USDT.BBP", "/USDT:USDT")
                    pos[symbol] = Decimal(str(d["position"])) * Decimal(str(self.market[symbol].precision.amount))
                except Exception as e:
                    print(e, d)
            print(pos)
            # EventSystem.emit("signal", pos)




async def main():
    try:
        exchange = BybitExchangeManager()
        signal = BybitSignal(exchange.market)
        await signal.receive()
    except Exception as e:
        print(e)


if __name__ == "__main__":
    asyncio.run(main())
