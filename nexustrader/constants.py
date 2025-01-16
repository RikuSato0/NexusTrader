import os
import sys
from typing import Literal, Union, Dict, List
from enum import Enum
from dynaconf import Dynaconf


def is_sphinx_build():
    return 'sphinx' in sys.modules

if not os.path.exists(".keys/"):
    os.makedirs(".keys/")
if not os.path.exists(".keys/.secrets.toml") and not is_sphinx_build():
    raise FileNotFoundError(
        "Config file not found, please create a config file at .keys/.secrets.toml"
    )


settings = Dynaconf(
    envvar_prefix="NEXUS",
    settings_files=['.keys/settings.toml', '.keys/.secrets.toml'],
    load_dotenv=True,
)

def get_redis_config(in_docker: bool = False):
    try:
        if in_docker:
            return {
                "host": "redis",
                "db": settings.REDIS_DB,
                "password": settings.REDIS_PASSWORD,
            }

        return {
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "db": settings.REDIS_DB,
            "password": settings.REDIS_PASSWORD,
        }
    except Exception as e:
        raise ValueError(f"Failed to get Redis password: {e}")


class Url:
    class Bybit:
        class Spot:
            MAINNET = "wss://stream.bybit.com/v5/public/spot"
            TESTNET = "wss://stream-testnet.bybit.com/v5/public/spot"

        class Linear:
            MAINNET = "wss://stream.bybit.com/v5/public/linear"
            TESTNET = "wss://stream-testnet.bybit.com/v5/public/linear"

        class Inverse:
            MAINNET = "wss://stream.bybit.com/v5/public/inverse"
            TESTNET = "wss://stream-testnet.bybit.com/v5/public/inverse"

        class Option:
            MAINNET = "wss://stream.bybit.com/v5/public/option"
            TESTNET = "wss://stream-testnet.bybit.com/v5/public/option"

    class Binance:
        class Spot:
            BASE_URL = "https://api.binance.com/api/v3/userDataStream"
            STREAM_URL = "wss://stream.binance.com:9443/ws"

        class Margin:
            BASE_URL = "https://api.binance.com/sapi/v1/userDataStream"
            STREAM_URL = "wss://stream.binance.com:9443/ws"

        class IsolatedMargin:
            BASE_URL = "https://api.binance.com/sapi/v1/userDataStream/isolated"
            STREAM_URL = "wss://stream.binance.com:9443/ws"

        class UsdMFuture:
            BASE_URL = "https://fapi.binance.com/fapi/v1/listenKey"
            STREAM_URL = "wss://fstream.binance.com/ws"

        class CoinMFuture:
            BASE_URL = "https://dapi.binance.com/dapi/v1/listenKey"
            STREAM_URL = "wss://dstream.binance.com/ws"

        class PortfolioMargin:
            BASE_URL = "https://papi.binance.com/papi/v1/listenKey"
            STREAM_URL = "wss://fstream.binance.com/pm/ws"

        class SpotTestnet:
            BASE_URL = "https://testnet.binance.vision/api/v3/userDataStream"
            STREAM_URL = "wss://testnet.binance.vision/ws"

        class UsdMFutureTestnet:
            BASE_URL = "https://testnet.binancefuture.com/fapi/v1/listenKey"
            STREAM_URL = "wss://stream.binancefuture.com/ws"

        class CoinMFutureTestnet:
            BASE_URL = "https://testnet.binancefuture.com/dapi/v1/listenKey"
            STREAM_URL = "wss://dstream.binancefuture.com/ws"

    class Okx:
        LIVE = "wss://ws.okx.com:8443/ws"
        AWS = "wss://wsaws.okx.com:8443/ws"
        DEMO = "wss://wspap.okx.com:8443/ws"

        # class Live:
        #     PUBLIC = "wss://ws.okx.com:8443/ws/v5/public"
        #     PRIVATE = "wss://ws.okx.com:8443/ws/v5/private"
        #     BUSINESS = "wss://ws.okx.com:8443/ws/v5/business"

        # class Aws:
        #     PUBLIC = "wss://wsaws.okx.com:8443/ws/v5/public"
        #     PRIVATE = "wss://wsaws.okx.com:8443/ws/v5/private"
        #     BUSINESS = "wss://wsaws.okx.com:8443/ws/v5/business"

        # class Demo:
        #     PUBLIC = "wss://wspap.okx.com:8443/ws/v5/public"
        #     PRIVATE = "wss://wspap.okx.com:8443/ws/v5/private"
        #     BUSINESS = "wss://wspap.okx.com:8443/ws/v5/business"


IntervalType = Literal[
    "1s",
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "6h",
    "8h",
    "12h",
    "1d",
    "3d",
    "1w",
    "1M",
]


UrlType = Union[
    Url.Binance.Spot,
    Url.Binance.Margin,
    Url.Binance.IsolatedMargin,
    Url.Binance.UsdMFuture,
    Url.Binance.CoinMFuture,
    Url.Binance.PortfolioMargin,
    Url.Binance.SpotTestnet,
    Url.Binance.UsdMFutureTestnet,
    Url.Binance.CoinMFutureTestnet,
    Url.Okx,
    Url.Bybit.Spot,
    Url.Bybit.Linear,
    Url.Bybit.Inverse,
    Url.Bybit.Option,
]

class SubmitType(Enum):
    CREATE = 0
    CANCEL = 1
    TWAP = 2
    CANCEL_TWAP = 3
    VWAP = 4
    CANCEL_VWAP = 5
class EventType(Enum):
    BOOKL1 = 0
    TRADE = 1
    KLINE = 2
    MARK_PRICE = 3
    FUNDING_RATE = 4
    INDEX_PRICE = 5


class AlgoOrderStatus(Enum):
    RUNNING = "RUNNING"
    CANCELING = "CANCELING"
    FINISHED = "FINISHED"
    CANCELED = "CANCELED"
    FAILED = "FAILED"

class OrderStatus(Enum):
    # LOCAL
    INITIALIZED = "INITIALIZED"
    FAILED = "FAILED"
    CANCEL_FAILED = "CANCEL_FAILED"

    # IN-FLOW
    PENDING = "PENDING"
    CANCELING = "CANCELING"

    # OPEN
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"

    # CLOSED
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class ExchangeType(Enum):
    BINANCE = "binance"
    OKX = "okx"
    BYBIT = "bybit"


class BinanceAccountType(Enum):
    SPOT = "SPOT"
    MARGIN = "MARGIN"
    ISOLATED_MARGIN = "ISOLATED_MARGIN"
    USD_M_FUTURE = "USD_M_FUTURE"
    COIN_M_FUTURE = "COIN_M_FUTURE"
    PORTFOLIO_MARGIN = "PORTFOLIO_MARGIN"
    SPOT_TESTNET = "SPOT_TESTNET"
    USD_M_FUTURE_TESTNET = "USD_M_FUTURE_TESTNET"
    COIN_M_FUTURE_TESTNET = "COIN_M_FUTURE_TESTNET"


class OkxAccountType(Enum):
    LIVE = 0
    AWS = 1
    DEMO = 2


class BybitAccountType(Enum):
    SPOT = 0
    LINEAR = 1
    INVERSE = 2
    OPTION = 3
    SPOT_TESTNET = 4
    LINEAR_TESTNET = 5
    INVERSE_TESTNET = 6
    OPTION_TESTNET = 7


STREAM_URLS = {
    BinanceAccountType.SPOT: "wss://stream.binance.com:9443/ws",
    BinanceAccountType.MARGIN: "wss://stream.binance.com:9443/ws",
    BinanceAccountType.ISOLATED_MARGIN: "wss://stream.binance.com:9443/ws",
    BinanceAccountType.USD_M_FUTURE: "wss://fstream.binance.com/ws",
    BinanceAccountType.COIN_M_FUTURE: "wss://dstream.binance.com/ws",
    BinanceAccountType.PORTFOLIO_MARGIN: "wss://fstream.binance.com/pm/ws",
    BinanceAccountType.SPOT_TESTNET: "wss://testnet.binance.vision/ws",
    BinanceAccountType.USD_M_FUTURE_TESTNET: "wss://stream.binancefuture.com/ws",
    BinanceAccountType.COIN_M_FUTURE_TESTNET: "wss://dstream.binancefuture.com/ws",
    OkxAccountType.LIVE: "wss://ws.okx.com:8443/ws",
    OkxAccountType.AWS: "wss://wsaws.okx.com:8443/ws",
    OkxAccountType.DEMO: "wss://wspap.okx.com:8443/ws",
    BybitAccountType.SPOT: "wss://stream.bybit.com/v5/public/spot",
    BybitAccountType.LINEAR: "wss://stream.bybit.com/v5/public/linear",
    BybitAccountType.INVERSE: "wss://stream.bybit.com/v5/public/inverse",
    BybitAccountType.OPTION: "wss://stream.bybit.com/v5/public/option",
    BybitAccountType.SPOT_TESTNET: "wss://stream-testnet.bybit.com/v5/public/spot",
    BybitAccountType.LINEAR_TESTNET: "wss://stream-testnet.bybit.com/v5/public/linear",
    BybitAccountType.INVERSE_TESTNET: "wss://stream-testnet.bybit.com/v5/public/inverse",
    BybitAccountType.OPTION_TESTNET: "wss://stream-testnet.bybit.com/v5/public/option",
}

LISTEN_KEY_URLS = {
    BinanceAccountType.SPOT: "https://api.binance.com/api/v3/userDataStream",
    BinanceAccountType.MARGIN: "https://api.binance.com/sapi/v1/userDataStream",
    BinanceAccountType.ISOLATED_MARGIN: "https://api.binance.com/sapi/v1/userDataStream/isolated",
    BinanceAccountType.USD_M_FUTURE: "https://fapi.binance.com/fapi/v1/listenKey",
    BinanceAccountType.COIN_M_FUTURE: "https://dapi.binance.com/dapi/v1/listenKey",
    BinanceAccountType.PORTFOLIO_MARGIN: "https://papi.binance.com/papi/v1/listenKey",
    BinanceAccountType.SPOT_TESTNET: "https://testnet.binance.vision/api/v3/userDataStream",
    BinanceAccountType.USD_M_FUTURE_TESTNET: "https://testnet.binancefuture.com/fapi/v1/listenKey",
    BinanceAccountType.COIN_M_FUTURE_TESTNET: "https://testnet.binancefuture.com/dapi/v1/listenKey",
}

BASE_URLS = {
    BinanceAccountType.SPOT: "https://api.binance.com",
    BinanceAccountType.MARGIN: "https://api.binance.com",
    BinanceAccountType.ISOLATED_MARGIN: "https://api.binance.com",
    BinanceAccountType.USD_M_FUTURE: "https://fapi.binance.com",
    BinanceAccountType.COIN_M_FUTURE: "https://dapi.binance.com",
    BinanceAccountType.PORTFOLIO_MARGIN: "https://papi.binance.com",
    BinanceAccountType.SPOT_TESTNET: "https://testnet.binance.vision",
    BinanceAccountType.USD_M_FUTURE_TESTNET: "https://testnet.binancefuture.com",
    BinanceAccountType.COIN_M_FUTURE_TESTNET: "https://testnet.binancefuture.com",
}


class BinanceEndpointsType(Enum):
    USER_DATA_STREAM = 0
    ACCOUNT = 1
    TRADING = 2
    MARKET = 3
    GENERAL = 4


BINANCE_ENDPOINTS = {
    BinanceEndpointsType.USER_DATA_STREAM: {
        BinanceAccountType.SPOT: "/api/v3/userDataStream",
        BinanceAccountType.MARGIN: "/sapi/v1/userDataStream",
        BinanceAccountType.ISOLATED_MARGIN: "/sapi/v1/userDataStream/isolated",
        BinanceAccountType.USD_M_FUTURE: "/fapi/v1/listenKey",
        BinanceAccountType.COIN_M_FUTURE: "/dapi/v1/listenKey",
        BinanceAccountType.PORTFOLIO_MARGIN: "/papi/v1/listenKey",
        BinanceAccountType.SPOT_TESTNET: "/api/v3/userDataStream",
        BinanceAccountType.USD_M_FUTURE_TESTNET: "/fapi/v1/listenKey",
        BinanceAccountType.COIN_M_FUTURE_TESTNET: "/dapi/v1/listenKey",
    },
    BinanceEndpointsType.TRADING: {
        BinanceAccountType.SPOT: "/api/v3",
        BinanceAccountType.MARGIN: "/sapi/v1",
        BinanceAccountType.ISOLATED_MARGIN: "/sapi/v1",
        BinanceAccountType.USD_M_FUTURE: "/fapi/v1",
        BinanceAccountType.COIN_M_FUTURE: "/dapi/v1",
        BinanceAccountType.PORTFOLIO_MARGIN: "/papi/v1",
        BinanceAccountType.SPOT_TESTNET: "/api/v3",
        BinanceAccountType.USD_M_FUTURE_TESTNET: "/fapi/v1",
        BinanceAccountType.COIN_M_FUTURE_TESTNET: "/dapi/v1",
    },
}


class WSType(Enum):
    BINANCE_SPOT = 0
    BINANCE_MARGIN = 1
    BINANCE_ISOLATED_MARGIN = 2
    BINANCE_USD_M_FUTURE = 3
    BINANCE_COIN_M_FUTURE = 4
    BINANCE_PORTFOLIO_MARGIN = 5
    BINANCE_SPOT_TESTNET = 6
    BINANCE_USD_M_FUTURE_TESTNET = 7
    OKX_LIVE = 8
    OKX_AWS = 9
    OKX_DEMO = 10


class PublicConnectorType(Enum):
    BINANCE_SPOT = 0
    BINANCE_USD_M_FUTURE = 1
    BINANCE_COIN_M_FUTURE = 2
    BINANCE_SPOT_TESTNET = 3
    BINANCE_USD_M_FUTURE_TESTNET = 4
    BINANCE_COIN_M_FUTURE_TESTNET = 5
    OKX_LIVE = 6
    OKX_AWS = 7
    OKX_DEMO = 8


class AccountType(Enum):
    pass


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class TimeInForce(Enum):
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class InstrumentType(Enum):
    SPOT = "spot"
    MARGIN = "margin"
    FUTURE = "future"
    OPTION = "option"
    SWAP = "swap"
    LINEAR = "linear"
    INVERSE = "inverse"


class OptionType(Enum):
    CALL = "call"
    PUT = "put"

STATUS_TRANSITIONS: Dict[OrderStatus, List[OrderStatus]] = {
    OrderStatus.PENDING: [
        OrderStatus.CANCELED,
        OrderStatus.CANCELING,
        OrderStatus.ACCEPTED,
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.CANCELED,
        OrderStatus.FILLED,
        OrderStatus.CANCEL_FAILED,
    ],
    OrderStatus.CANCELING: [
        OrderStatus.CANCELED,
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
    ],
    OrderStatus.ACCEPTED: [
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCELING,
        OrderStatus.CANCELED,
        OrderStatus.EXPIRED,
        OrderStatus.CANCEL_FAILED,
    ],
    OrderStatus.PARTIALLY_FILLED: [
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCELING,
        OrderStatus.CANCELED,
        OrderStatus.EXPIRED,
        OrderStatus.CANCEL_FAILED,
    ],
    OrderStatus.FILLED: [],
    OrderStatus.CANCELED: [],
    OrderStatus.EXPIRED: [],
    OrderStatus.FAILED: [],
}


class DataType(Enum):
    BOOKL1 = "bookl1"
    BOOKL2 = "bookl2"
    TRADE = "trade"
    KLINE = "kline"
    MARK_PRICE = "mark_price"
    FUNDING_RATE = "funding_rate"
    INDEX_PRICE = "index_price"

class StorageBackend(Enum):
    REDIS = "redis"
    SQLITE = "sqlite"
