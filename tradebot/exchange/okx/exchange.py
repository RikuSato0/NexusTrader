from typing import Any, Dict
from tradebot.base import ExchangeManager
import ccxt
import orjson
import msgspec
from tradebot.exchange.okx.types import OkxMarket


class OkxExchangeManager(ExchangeManager):
    api: ccxt.okx
    market: Dict[str, OkxMarket]
    market_id: Dict[str, OkxMarket]

    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        config["exchange_id"] = config.get("exchange_id", "okx")
        super().__init__(config)
        self.passphrase = config.get("password", None)

    def load_markets(self):
        market = self.api.load_markets()
        for k, v in market.items():
            v_json = orjson.dumps(v)
            v = msgspec.json.decode(v_json, type=OkxMarket)

            self.market[k] = v
            for _, v in self.market.items():
                self.market_id[v.id] = v
