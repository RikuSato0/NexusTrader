import asyncio
from collections import defaultdict
from nexustrader.schema import Trade
from nexustrader.core import Strategy
from nexustrader.exchange.binance import (
    BinanceAccountType,
    BinanceExchangeManager,
    BinancePublicConnector,
)
from nexustrader.exchange.okx import OkxAccountType, OkxExchangeManager, OkxPublicConnector


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

        conn_okx = OkxPublicConnector(
            OkxAccountType.LIVE,
            okx
        )

        conn_bnc = BinancePublicConnector(
            BinanceAccountType.USD_M_FUTURE,
            binance
        )

        demo = Demo()

        demo.add_public_connector(conn_okx)
        demo.add_public_connector(conn_bnc)

        await demo.subscribe_trade(BinanceAccountType.USD_M_FUTURE, "BTC/USDT:USDT")
        await demo.subscribe_trade(OkxAccountType.LIVE, "BTC/USDT:USDT")

        await demo.run()

    except asyncio.CancelledError:
        await binance.close()
        await okx.close()
        await conn_okx.disconnect()
        await conn_bnc.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
