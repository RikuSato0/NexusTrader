from pybit.unified_trading import WebSocket
from time import sleep
from tradebot.constants import settings

BYBIT_API_KEY = settings.BYBIT.ACCOUNT1.api_key
BYBIT_SECRET = settings.BYBIT.ACCOUNT1.secret

ws = WebSocket(
    testnet=True,
    channel_type="private",
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_SECRET,
)
def handle_message(message):
    print(message)
ws.position_stream(callback=handle_message)
while True:
    sleep(1)
