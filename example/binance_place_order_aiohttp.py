import asyncio
from pprint import pprint
from tradebot.constants import KEYS
from tradebot.base import ExchangeManager
from tradebot.exchange.binance.constants import BinanceAccountType
from tradebot.exchange.binance.rest_api import BinanceApiClient


BINANCE_API_KEY = KEYS["binance_future_testnet"]["API_KEY"]
BINANCE_API_SECRET = KEYS["binance_future_testnet"]["SECRET"]

# BINANCE_API_KEY = KEYS['binance_vip']['API_KEY']
# BINANCE_API_SECRET = KEYS['binance_vip']['SECRET']


async def main():
    try:
        # config = {
        #     'exchange_id': 'binance',
        #     'sandbox': False,
        #     'apiKey': BINANCE_API_KEY,
        #     'secret': BINANCE_API_SECRET,
        #     'enableRateLimit': False,
        #     'options': {
        #         'portfolioMargin': True,
        #     }
        # }

        config = {
            "exchange_id": "binance",
            "sandbox": True,
            "apiKey": BINANCE_API_KEY,
            "secret": BINANCE_API_SECRET,
            "enableRateLimit": False,
        }

        exchange = ExchangeManager(config)

        rest_api = BinanceApiClient(
            account_type=BinanceAccountType.USD_M_FUTURE_TESTNET,
            api_key=BINANCE_API_KEY,
            secret=BINANCE_API_SECRET,
        )

        res = await rest_api.place_market_order(
            symbol="BTCUSDT",
            side="sell",
            # price=62000,
            amount=0.01,
            # positionSide="SHORT",
            # reduceOnly=True,
        )

        pprint(res)

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
    finally:
        await rest_api.close_session()


if __name__ == "__main__":
    asyncio.run(main())
