import warnings

import ccxt
from abc import ABC, abstractmethod
from typing import Dict, Any
from nexustrader.schema import BaseMarket
from nexustrader.constants import ExchangeType
from nexustrader.core.log import SpdLog




class ExchangeManager(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("apiKey", None)
        self.secret = config.get("secret", None)
        self.exchange_id = ExchangeType(config["exchange_id"])
        self.api = self._init_exchange()
        self._log = SpdLog.get_logger(
            name=type(self).__name__, level="DEBUG", flush=True
        )
        self.is_testnet = config.get("sandbox", False)
        self.market: Dict[str, BaseMarket] = {}
        self.market_id: Dict[str, str] = {}

        if not self.api_key or not self.secret:
            warnings.warn(
                "API Key and Secret not provided, So some features related to trading will not work"
            )
        self.load_markets()

    def _init_exchange(self) -> ccxt.Exchange:
        """
        Initialize the exchange
        """
        try:
            exchange_class = getattr(ccxt, self.config["exchange_id"])
        except AttributeError:
            raise AttributeError(
                f"Exchange {self.config['exchange_id']} is not supported"
            )

        api = exchange_class(self.config)
        api.set_sandbox_mode(
            self.config.get("sandbox", False)
        )  # Set sandbox mode if demo trade is enabled
        return api

    def _parse_symbol(self, mkt: BaseMarket, exchange_suffix: str) -> str:
        """
        Parse the symbol for the exchange
        """
        if mkt.spot:
            return f"{mkt.base}{mkt.quote}.{exchange_suffix}"
        elif mkt.future:
            symbol = mkt.symbol
            expiry_suffix = symbol.split("-")[-1]
            return f"{mkt.base}{mkt.quote}-{expiry_suffix}.{exchange_suffix}"
        elif mkt.linear:
            return f"{mkt.base}{mkt.quote}-PERP.{exchange_suffix}"
        elif mkt.inverse:
            return f"{mkt.base}{mkt.quote}-PERP.{exchange_suffix}"

    @abstractmethod
    def load_markets(self):
        pass

    @property
    def linear(self):
        symbols = []
        for symbol, market in self.market.items():
            if market.linear and market.active and not market.future:
                symbols.append(symbol)
        return symbols

    @property
    def inverse(self):
        symbols = []
        for symbol, market in self.market.items():
            if market.inverse and market.active and not market.future:
                symbols.append(symbol)
        return symbols

    @property
    def spot(self):
        symbols = []
        for symbol, market in self.market.items():
            if market.spot and market.active:
                symbols.append(symbol)
        return symbols

    @property
    def future(self):
        symbols = []
        for symbol, market in self.market.items():
            if market.future and market.active:
                symbols.append(symbol)
        return symbols
