import asyncio
import uvloop
from tradebot.entity import EventSystem
from tradebot.exchange import BinanceWSManager, BinanceExchangeManager
from tradebot.constants import BinanceAccountType, EventType
from tradebot.log import SpdLog


@EventSystem.on(EventType.BOOKL1)
def on_bookl1(data):
    print(data)

@EventSystem.on(EventType.TRADE)
def on_trade(data):
    print(data)

@EventSystem.on(EventType.KLINE)
def on_kline(data):
    print(data)

async def main():
    try:
        SpdLog.initialize()
        
        config = {
            "exchange_id": "binance",
            "enableRateLimit": False,
        }
        
        exchange = BinanceExchangeManager(config)
        await exchange.load_markets()
        binance_ws_manager = BinanceWSManager(BinanceAccountType.SPOT, exchange)
        
        await binance_ws_manager.connect()
        # await binance_ws_manager.subscribe_book_ticker("BTCUSDT")
        # await binance_ws_manager.subscribe_trade("BTCUSDT")
        await binance_ws_manager.subscribe_kline("BTCUSDT", "1s")
        
        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        await exchange.close()
        binance_ws_manager.disconnect()
        print("Websocket closed")


if __name__ == "__main__":
    uvloop.run(main())
