import asyncio
from tradebot.constants import CONFIG
from tradebot.exchange.okx import OkxAccountType, OkxPrivateConnector, OkxExchangeManager, OkxPublicConnector


OKX_API_KEY = CONFIG['okex_demo']['API_KEY']
OKX_SECRET = CONFIG['okex_demo']['SECRET']
OKX_PASSPHRASE = CONFIG['okex_demo']['PASSPHRASE']


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
