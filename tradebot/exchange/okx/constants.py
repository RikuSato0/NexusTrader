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


from nautilus_trader.adapters.okx.schemas.ws import OKXWsAccountPushDataMsg
from nautilus_trader.adapters.okx.schemas.ws import OKXWsPositionsPushDataMsg
from nautilus_trader.adapters.okx.schemas.ws import OKXWsFillsPushDataMsg
from nautilus_trader.adapters.okx.schemas.ws import OKXWsOrdersPushDataMsg
from nautilus_trader.adapters.okx.schemas.ws import OKXWsGeneralMsg
from nautilus_trader.adapters.okx.schemas.ws import OKXWsOrderbookPushDataMsg
from nautilus_trader.adapters.okx.schemas.ws import OKXWsPushDataMsg
