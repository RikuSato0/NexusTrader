import os
import ccxt

from configparser import ConfigParser
from collections import defaultdict

from typing import Literal, Union

from enum import Enum




if not os.path.exists('.keys/'):
    os.makedirs('.keys/')
if not os.path.exists('.keys/config.cfg'):
    raise FileNotFoundError("Config file not found, please create a config file at .keys/config.cfg")

CONFIG = ConfigParser()
CONFIG.read('.keys/config.cfg')

# API_KEY = CONFIG['binance_2']['API_KEY']
# API_SECRET = CONFIG['binance_2']['SECRET']

# API_KEY_TESTNET = CONFIG['binance_future_testnet']['API_KEY']
# API_SECRET_TESTNET = CONFIG['binance_future_testnet']['SECRET']


# API_KEY_UNI = CONFIG['binance_uni']['API_KEY']
# API_SECRET_UNI = CONFIG['binance_uni']['SECRET']

# BYBIT_API_KEY = config['bybit']['API_KEY']
# BYBIT_SECRET = config['bybit']['SECRET']
# VALID_SYMBOLS = CONFIG['symbols']['VALID_SYMBOLS'].split(' ')

# OKX_API_KEY = CONFIG['okex_demo']['API_KEY']
# OKX_SECRET = CONFIG['okex_demo']['SECRET']
# OKX_PASSPHRASE = CONFIG['okex_demo']['PASSPHRASE']
# OKX_USER = CONFIG['okex_demo']['USER']

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


IntervalType = Literal["1s", "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]


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



class EventType(Enum):
    BOOKL1 = 0
    TRADE = 1
    KLINE = 2
    MARK_PRICE = 3
    FUNDING_RATE = 4
    INDEX_PRICE = 5

class ExchangeType(Enum):
    BINANCE = 0
    OKX = 1
    BYBIT = 2






class BinanceAccountType(Enum):
    SPOT = 0
    MARGIN = 1
    ISOLATED_MARGIN = 2
    USD_M_FUTURE = 3
    COIN_M_FUTURE = 4
    PORTFOLIO_MARGIN = 5
    SPOT_TESTNET = 6
    USD_M_FUTURE_TESTNET = 7
    COIN_M_FUTURE_TESTNET = 8


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
    Trading = 2
    Market = 3
    General = 4


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
    
    BinanceEndpointsType.ACCOUNT: {
        BinanceAccountType.SPOT: "/api/v3/account",
        BinanceAccountType.MARGIN: "/sapi/v1/margin/account",
        BinanceAccountType.ISOLATED_MARGIN: "/sapi/v1/margin/isolated/account",
        BinanceAccountType.USD_M_FUTURE: "/fapi/v2/account",
        BinanceAccountType.COIN_M_FUTURE: "/dapi/v1/account",
        BinanceAccountType.PORTFOLIO_MARGIN: "/papi/v1/account",
        BinanceAccountType.SPOT_TESTNET: "/api/v3/account",
        BinanceAccountType.USD_M_FUTURE_TESTNET: "/fapi/v2/account",
        BinanceAccountType.COIN_M_FUTURE_TESTNET: "/dapi/v1/account",
    }
}
