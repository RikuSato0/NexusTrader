from enum import Enum

class EventType(Enum):
    BOOKL1 = 0
    TRADE = 1
    KLINE = 2
    MARK_PRICE = 3
    FUNDING_RATE = 4
    INDEX_PRICE = 5

class AccountType(Enum):
    SPOT = "SPOT"
    MARGIN = "MARGIN"
    ISOLATED_MARGIN = "ISOLATED_MARGIN"
    USD_M_FUTURE = "USD_M_FUTURE"
    COIN_M_FUTURE = "COIN_M_FUTURE"
    PORTFOLIO_MARGIN = "PORTFOLIO_MARGIN"
    SPOT_TESTNET = "SPOT_TESTNET"
    USD_M_FUTURE_TESTNET = "USD_M_FUTURE_TESTNET"
    COIN_M_FUTURE_TESTNET = "COIN_M_FUTURE_TESTNET"

class EndpointsType(Enum):
    USER_DATA_STREAM = "USER_DATA_STREAM"
    ACCOUNT = "ACCOUNT"
    TRADING = "TRADING"
    MARKET = "MARKET"
    GENERAL = "GENERAL"

BASE_URLS = {
    AccountType.SPOT: "https://api.binance.com",
    AccountType.MARGIN: "https://api.binance.com",
    AccountType.ISOLATED_MARGIN: "https://api.binance.com",
    AccountType.USD_M_FUTURE: "https://fapi.binance.com",
    AccountType.COIN_M_FUTURE: "https://dapi.binance.com",
    AccountType.PORTFOLIO_MARGIN: "https://papi.binance.com",
    AccountType.SPOT_TESTNET: "https://testnet.binance.vision",
    AccountType.USD_M_FUTURE_TESTNET: "https://testnet.binancefuture.com",
    AccountType.COIN_M_FUTURE_TESTNET: "https://testnet.binancefuture.com",
}

STREAM_URLS = {
    AccountType.SPOT: "wss://stream.binance.com:9443/ws",
    AccountType.MARGIN: "wss://stream.binance.com:9443/ws",
    AccountType.ISOLATED_MARGIN: "wss://stream.binance.com:9443/ws",
    AccountType.USD_M_FUTURE: "wss://fstream.binance.com/ws",
    AccountType.COIN_M_FUTURE: "wss://dstream.binance.com/ws",
    AccountType.PORTFOLIO_MARGIN: "wss://fstream.binance.com/ws",
    AccountType.SPOT_TESTNET: "wss://testnet.binance.vision/ws",
    AccountType.USD_M_FUTURE_TESTNET: "wss://stream.binancefuture.com/ws",
    AccountType.COIN_M_FUTURE_TESTNET: "wss://dstream.binancefuture.com/ws",
}

ENDPOINTS = {
    EndpointsType.USER_DATA_STREAM: {
        AccountType.SPOT: "/api/v3/userDataStream",
        AccountType.MARGIN: "/sapi/v1/userDataStream",
        AccountType.ISOLATED_MARGIN: "/sapi/v1/userDataStream/isolated",
        AccountType.USD_M_FUTURE: "/fapi/v1/listenKey",
        AccountType.COIN_M_FUTURE: "/dapi/v1/listenKey",
        AccountType.PORTFOLIO_MARGIN: "/papi/v1/listenKey",
        AccountType.SPOT_TESTNET: "/api/v3/userDataStream",
        AccountType.USD_M_FUTURE_TESTNET: "/fapi/v1/listenKey",
        AccountType.COIN_M_FUTURE_TESTNET: "/dapi/v1/listenKey",
    },
    EndpointsType.TRADING: {
        AccountType.SPOT: "/api/v3",
        AccountType.MARGIN: "/sapi/v1",
        AccountType.ISOLATED_MARGIN: "/sapi/v1",
        AccountType.USD_M_FUTURE: "/fapi/v1",
        AccountType.COIN_M_FUTURE: "/dapi/v1",
        AccountType.PORTFOLIO_MARGIN: "/papi/v1",
        AccountType.SPOT_TESTNET: "/api/v3",
        AccountType.USD_M_FUTURE_TESTNET: "/fapi/v1",
        AccountType.COIN_M_FUTURE_TESTNET: "/dapi/v1",
    },
}
