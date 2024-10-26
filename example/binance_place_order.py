import time
import asyncio
from pprint import pprint
from tradebot.constants import CONFIG
from tradebot.base import ExchangeManager
from tradebot.exchange._binance import BinanceOrderManager
from tradebot.exchange.binance import BinancePrivateConnector, BinanceAccountType, BinanceExchangeManager
from tradebot.exceptions import OrderError


BINANCE_API_KEY = CONFIG["binance_future_testnet"]["API_KEY"]
BINANCE_API_SECRET = CONFIG["binance_future_testnet"]["SECRET"]

# BINANCE_API_KEY = CONFIG['binance_vip']['API_KEY']
# BINANCE_API_SECRET = CONFIG['binance_vip']['SECRET']


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

        exchange = BinanceExchangeManager(config)
        await exchange.load_markets()
        
        private_conn = BinancePrivateConnector(
            account_type=BinanceAccountType.USD_M_FUTURE_TESTNET,
            api_key=BINANCE_API_KEY,
            secret=BINANCE_API_SECRET,
            market=exchange.market,
            market_id=exchange.market_id,
        )
        
        await private_conn._api_client.init_session()
        
        order_manager = BinanceOrderManager(exchange)
        start = int(time.time() * 1000)
        res = await order_manager.place_limit_order(
            symbol="BTC/USDT:USDT",
            side="sell",
            price=62000,
            amount=0.01,
            positionSide="SHORT",
        )
        end = int(time.time() * 1000)
        print(f"CCXT Time: {end - start} ms")
        
        start = int(time.time() * 1000)   
        res = await private_conn.create_order(
            symbol='BTC/USDT:USDT',
            side='sell',
            type="limit",
            price=62000,
            amount=0.01,
            positionSide="SHORT",
        )
        end = int(time.time() * 1000)
        
        print(f"Tradebot Time: {end - start} ms")

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

    except OrderError as e:
        print(e)
    finally:
        await private_conn.disconnect()
        await exchange.close()


if __name__ == "__main__":
    asyncio.run(main())
