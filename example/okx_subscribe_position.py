import asyncio
import uvloop


from nexustrader.exchange.okx.websockets import OkxWSClient
from nexustrader.constants import KEYS, Url
from nexustrader.exchange.okx import OkxAccountType

OKX_API_KEY = KEYS["okex_demo"]["API_KEY"]
OKX_SECRET = KEYS["okex_demo"]["SECRET"]
OKX_PASSPHRASE = KEYS["okex_demo"]["PASSPHRASE"]


def cb(msg):
    print(msg)


async def main():
    try:
        okx_ws_manager = OkxWSClient(
            account_type=OkxAccountType.DEMO,
            handler=cb,
            api_key=OKX_API_KEY,
            secret=OKX_SECRET,
            passphrase=OKX_PASSPHRASE,
        )
        await okx_ws_manager.subscribe_positions()

        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("Websocket closed.")


if __name__ == "__main__":
    uvloop.run(main())
