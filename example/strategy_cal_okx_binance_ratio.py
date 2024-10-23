import asyncio
from collections import defaultdict
from tradebot.types import Trade
from tradebot.constants import WSType
from tradebot.strategy import Strategy
from tradebot.exchange.binance import (
    BinanceWSManager,
    BinanceAccountType,
    BinanceExchangeManager,
)
from tradebot.exchange.okx import OkxWSManager, OkxAccountType, OkxExchangeManager


class Demo(Strategy):
    def __init__(self):
        super().__init__(tick_size=0.01)
        self.market = defaultdict(dict)

    def on_trade(self, trade: Trade):
        self.market[trade.exchange][trade.symbol] = trade

    def on_tick(self, tick):
        btc_binance = self.market["binance"].get("BTC/USDT:USDT", None)
        btc_okx = self.market["okx"].get("BTC/USDT:USDT", None)
        if btc_binance and btc_okx:
            print(
                f"binance: {btc_binance.price}, okx: {btc_okx.price}, ratio: {btc_binance.price / btc_okx.price - 1}"
            )
        


async def main():
    try:
        binance = BinanceExchangeManager({"exchange_id": "binance"})
        await binance.load_markets()  # get `market` and `market_id` data
        
        okx = OkxExchangeManager({"exchange_id": "okx"})
        await okx.load_markets()  # get `market` and `market_id` data

        ws_okx = OkxWSManager(
            OkxAccountType.LIVE,
            okx.market,
            okx.market_id,
        )

        ws_usdm = BinanceWSManager(
            BinanceAccountType.USD_M_FUTURE,
            binance.market,
            binance.market_id,
        )
        await ws_okx.connect()
        await ws_usdm.connect()

        demo = Demo()

        demo.add_ws_manager(WSType.OKX_LIVE, ws_okx)
        demo.add_ws_manager(WSType.BINANCE_USD_M_FUTURE, ws_usdm)

        await demo.subscribe_trade(WSType.BINANCE_USD_M_FUTURE, "BTC/USDT:USDT")
        await demo.subscribe_trade(WSType.OKX_LIVE, "BTC/USDT:USDT")

        await demo.run()

    except asyncio.CancelledError:
        await binance.close()
        await okx.close()
        ws_usdm.disconnect()
        ws_okx.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
