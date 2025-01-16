import time
import asyncio
from nexustrader.constants import KEYS
from nexustrader.base import ExchangeManager
from nexustrader.exchange.binance import (
    BinancePrivateConnector,
    BinanceAccountType,
    BinanceExchangeManager,
)


BINANCE_API_KEY = KEYS["binance_future_testnet"]["API_KEY"]
BINANCE_API_SECRET = KEYS["binance_future_testnet"]["SECRET"]


async def test_tradebot(n: int = 20, exchange: ExchangeManager = None):
    lat = []
    private_conn = BinancePrivateConnector(
        account_type=BinanceAccountType.USD_M_FUTURE_TESTNET,
        market=exchange.market,
        market_id=exchange.market_id,
        api=exchange.api,
    )

    for i in range(n):
        start = int(time.time() * 1000)
        res = await private_conn.create_order(
            symbol="BTC/USDT:USDT",
            side="sell",
            type="market",
            amount=0.01,
            positionSide="SHORT",
        )
        end = int(time.time() * 1000)

        lat.append(end - start)

        start = int(time.time() * 1000)
        res = await private_conn.create_order(
            symbol="BTC/USDT:USDT",
            side="buy",
            type="market",
            amount=0.01,
            positionSide="SHORT",
        )
        end = int(time.time() * 1000)

        lat.append(end - start)
        await asyncio.sleep(0.2)

    print(f"Tradebot Time: {sum(lat) / len(lat)} ms")
    await private_conn.disconnect()


async def main():
    try:
        config = {
            "exchange_id": "binance",
            "sandbox": True,
            "apiKey": BINANCE_API_KEY,
            "secret": BINANCE_API_SECRET,
            "enableRateLimit": False,
        }

        exchange = BinanceExchangeManager(config)
        await exchange.load_markets()

        private_conn = BinancePrivateConnector(
            account_type=BinanceAccountType.USD_M_FUTURE_TESTNET,
            exchange=exchange,
        )

        res = await private_conn.place_limit_order(
            symbol="BTC/USDT:USDT",
            side="buy",
            amount=0.01,
            price=68300.6,
            positionSide="LONG",
        )

        print(res)

        # await test_ccxt(30, exchange)
        # await test_tradebot(30, exchange)

        # pprint(res)

        # res = await order_manager.place_limit_order(
        #     symbol="BTC/USDT:USDT",
        #     side="buy",
        #     price=62000,
        #     amount=0.01,
        #     positionSide="SHORT",
        #     # reduceOnly=True,
        # )

        # pprint(res)

        # res = await order_manager.place_limit_order(
        #     symbol="BTC/USDT:USDT",
        #     side="buy",
        #     price=62000,
        #     amount=0.01,
        #     positionSide="SHORT",
        #     # reduceOnly=True,
        # )

        # pprint(res)

        # res = await order_manager.cancel_order(
        #     id = res.id,
        #     symbol='BTC/USDT:USDT',
        # )

        # pprint(res)

        # res = await order_manager.fetch_orders(
        #     symbol="ICP/USDT:USDT",
        # )
        # orders = {}

        # for order in res:
        #     datetime = pd.to_datetime(order.timestamp, unit='ms')
        #     orders[datetime] = order

        # pprint(orders)

        # res = await order_manager.place_market_order(
        #     symbol='BNB/USDT',
        #     side='sell',
        #     amount=0.564,
        #     # reduceOnly=True,
        # )

        # pprint(res)

        # res = await order_manager.place_limit_order(
        #     symbol='USDC/USDT:USDT',
        #     side='buy',
        #     amount=10,
        #     price=0.95,
        #     newClientOrderId='test',
        # )

        # pprint(res)

        # await asyncio.sleep(1)

        # res = await order_manager.cancel_order(
        #     id=res.id,
        #     symbol='USDC/USDT:USDT',
        # )

        # pprint(res)

    except Exception as e:
        print(e)


if __name__ == "__main__":
    asyncio.run(main())
