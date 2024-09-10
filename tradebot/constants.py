import os

from configparser import ConfigParser
from collections import defaultdict


config = ConfigParser()

if not os.path.exists('.keys/'):
    os.makedirs('.keys/')
if not os.path.exists('.keys/config.cfg'):
    raise FileNotFoundError("Config file not found, please create a config file at .keys/config.cfg")

config.read('.keys/config.cfg')

API_KEY = config['binance_2']['API_KEY']
API_SECRET = config['binance_2']['SECRET']

API_KEY_UNI = config['binance_uni']['API_KEY']
API_SECRET_UNI = config['binance_uni']['SECRET']
VALID_SYMBOLS = config['symbols']['VALID_SYMBOLS'].split(' ')

OKX_API_KEY = config['okex_demo']['API_KEY']
OKX_API_SECRET = config['okex_demo']['SECRET']
OKX_PASSPHRASE = config['okex_demo']['PASSPHRASE']

LATENCY = defaultdict(list)

OPEN_RATIO = []
CLOSE_RATIO = []

MARKET_URLS = {
    "binance": {
        "spot": {
            "base_url": "https://api.binance.com/api/v3/userDataStream",
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
    
    "okex": {
        "public": "wss://ws.okx.com:8443/ws/v5/public",
        "private": "wss://ws.okx.com:8443/ws/v5/private",
        "business": "wss://ws.okx.com:8443/ws/v5/business",
    }
}


