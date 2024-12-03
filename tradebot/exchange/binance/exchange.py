import ccxt
import orjson
import msgspec
from typing import Any, Dict
from ...base import ExchangeManager
from .types import BinanceMarket


class BinanceExchangeManager(ExchangeManager):
    api: ccxt.binance
    market: Dict[str, BinanceMarket] 
    market_id: Dict[str, BinanceMarket]
    
    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        config["exchange_id"] = config.get("exchange_id", "binance")
        super().__init__(config)

    def load_markets(self):
        market = self.api.load_markets()
        for k,v in market.items():
            try:
                v_json = orjson.dumps(v)
                v = msgspec.json.decode(v_json, type=BinanceMarket)
                
                self.market[k] = v
                if v.type.value == "spot":
                    self.market_id[f"{v.id}_spot"] = v
                elif v.linear:
                    self.market_id[f"{v.id}_linear"] = v
                elif v.inverse:
                    self.market_id[f"{v.id}_inverse"] = v
                
            except Exception as e:
                print(f"Error: {e}, {k}, {v}")
                continue
        
        
    #     self._get_market_id()

    # def _get_market_id(self):
    #     self.market_id = {}
    #     if not self.market:
    #         raise ValueError(
    #             "Market data not loaded, please call `load_markets()` first"
    #         )
    #     for _, v in self.market.items():
    #         if v["type"] == "spot":
    #             self.market_id[f"{v['id']}_spot"] = v
    #         elif v["linear"]:
    #             self.market_id[f"{v['id']}_linear"] = v
    #         elif v["inverse"]:
    #             self.market_id[f"{v['id']}_inverse"] = v
