from enum import Enum
from tradebot.constants import AccountType

class OkxAccountType(AccountType):
    LIVE = 0
    AWS = 1
    DEMO = 2
    
STREAM_URLS = {
    OkxAccountType.LIVE: "wss://ws.okx.com:8443/ws",
    OkxAccountType.AWS: "wss://wsaws.okx.com:8443/ws",
    OkxAccountType.DEMO: "wss://wspap.okx.com:8443/ws",
}
