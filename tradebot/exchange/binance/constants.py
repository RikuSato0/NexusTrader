from enum import Enum


class OrderStatus(Enum):
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    EXPIRED = "expired"
    FAILED = "failed"

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
    
    @property
    def is_spot(self):
        return self in (self.SPOT, self.SPOT_TESTNET)
    
    @property
    def is_margin(self):
        return self in (self.MARGIN, self.ISOLATED_MARGIN)
    
    @property
    def is_spot_or_margin(self):
        return self in (self.SPOT, self.MARGIN, self.ISOLATED_MARGIN, self.SPOT_TESTNET)
    
    @property
    def is_future(self):
        return self in (self.USD_M_FUTURE, self.COIN_M_FUTURE, self.USD_M_FUTURE_TESTNET, self.COIN_M_FUTURE_TESTNET)
    
    @property
    def is_linear(self):
        return self in (self.USD_M_FUTURE, self.USD_M_FUTURE_TESTNET)
    
    @property
    def is_inverse(self):
        return self in (self.COIN_M_FUTURE, self.COIN_M_FUTURE_TESTNET)

    @property
    def is_portfolio_margin(self):
        return self in (self.PORTFOLIO_MARGIN,)
    

class EndpointsType(Enum):
    USER_DATA_STREAM = "USER_DATA_STREAM"
    ACCOUNT = "ACCOUNT"
    TRADING = "TRADING"
    MARKET = "MARKET"
    GENERAL = "GENERAL"

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
}

ENDPOINTS = {
    EndpointsType.USER_DATA_STREAM: {
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
    EndpointsType.TRADING: {
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
