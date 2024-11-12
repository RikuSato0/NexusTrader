import asyncio
from tradebot.constants import CONFIG
from tradebot.exchange.okx import OkxAccountType, OkxPrivateConnector, OkxExchangeManager, OkxPublicConnector
from tradebot.constants import EventType
from tradebot.entity import EventSystem

OKX_API_KEY = CONFIG['okex_demo']['API_KEY']
OKX_SECRET = CONFIG['okex_demo']['SECRET']
OKX_PASSPHRASE = CONFIG['okex_demo']['PASSPHRASE']



EventSystem.on(EventType.ORDER_CREATED, lambda x: print(x))


async def main():
    try:
        config = {
            'exchange_id': 'okx',
            'sandbox': True,
            'apiKey': OKX_API_KEY,
            'secret': OKX_SECRET,
            'password': OKX_PASSPHRASE,
            'enableRateLimit': False,
        }
        
        exchange = OkxExchangeManager(config)
        
        private_conn = OkxPrivateConnector(
            account_type=OkxAccountType.DEMO,
            exchange=exchange,
        )
        
        await private_conn.connect()
        
        while True:
            await asyncio.sleep(1)
        
    except asyncio.CancelledError:
        await private_conn.disconnect()
        print("Connection closed.")

if __name__ == "__main__":
    asyncio.run(main())
