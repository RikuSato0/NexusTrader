import os

from configparser import ConfigParser
from collections import defaultdict

from enum import Enum

from typing import Literal, Union


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
        class Live:
            PUBLIC = "wss://ws.okx.com:8443/ws/v5/public"
            PRIVATE = "wss://ws.okx.com:8443/ws/v5/private"
            BUSINESS = "wss://ws.okx.com:8443/ws/v5/business"

        class Aws:
            PUBLIC = "wss://wsaws.okx.com:8443/ws/v5/public"
            PRIVATE = "wss://wsaws.okx.com:8443/ws/v5/private"
            BUSINESS = "wss://wsaws.okx.com:8443/ws/v5/business"

        class Demo:
            PUBLIC = "wss://wspap.okx.com:8443/ws/v5/public"
            PRIVATE = "wss://wspap.okx.com:8443/ws/v5/private"
            BUSINESS = "wss://wspap.okx.com:8443/ws/v5/business"




MARKET_URLS = {
    "binance": {
        "spot": {
            "base_url": "https://api.binance.com/api/v3/userDataStream",
            "stream_url": "wss://stream.binance.com:9443/ws/"
        },
        "margin": {
            "base_url": "https://api.binance.com/sapi/v1/userDataStream",
            "stream_url": "wss://stream.binance.com:9443/ws/"
        },
        "isolated-margin": {
            "base_url": "https://api.binance.com/sapi/v1/userDataStream/isolated",
            "stream_url": "wss://stream.binance.com:9443/ws/"
        },
        "linear": {
            "base_url": "https://fapi.binance.com/fapi/v1/listenKey",
            "stream_url": "wss://fstream.binance.com/ws/"
        },
        "inverse": {
            "base_url": "https://dapi.binance.com/dapi/v1/listenKey",
            "stream_url": "wss://dstream.binance.com/ws/"
        },
        "portfolio": {
            "base_url": "https://papi.binance.com/papi/v1/listenKey",
            "stream_url": "wss://fstream.binance.com/pm/ws/"
        }
    },
    
    "okx": {
        "live": {
            "public": "wss://ws.okx.com:8443/ws/v5/public",
            "private": "wss://ws.okx.com:8443/ws/v5/private",
            "business": "wss://ws.okx.com:8443/ws/v5/business",
        },
        "aws": {
            "public": "wss://wsaws.okx.com:8443/ws/v5/public",
            "private": "wss://wsaws.okx.com:8443/ws/v5/private",
            "business": "wss://wsaws.okx.com:8443/ws/v5/business",
        },
        "demo": {
            "public": "wss://wspap.okx.com:8443/ws/v5/public",
            "private": "wss://wspap.okx.com:8443/ws/v5/private",
            "business": "wss://wspap.okx.com:8443/ws/v5/business",
        }
    }
}


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
    Url.Okx.Live,
    Url.Okx.Aws,
    Url.Okx.Demo
]
