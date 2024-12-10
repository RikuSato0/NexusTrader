import ccxt
import orjson
import msgspec
from typing import Any, Dict
from tradebot.base import ExchangeManager
from tradebot.exchange.binance.types import BinanceMarket


class BinanceExchangeManager(ExchangeManager):
    api: ccxt.binance
    market: Dict[str, BinanceMarket] 
    market_id: Dict[str, BinanceMarket]
    
    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        config["exchange_id"] = config.get("exchange_id", "binance")
        super().__init__(config)
    
    def parse_symbol(self, bm: BinanceMarket) -> str:
        if bm.spot:
            return f"{bm.base}{bm.quote}.BINANCE"
        elif bm.future:
            symbol = bm.symbol
            expiry_suffix = symbol.split("-")[-1]
            return f"{bm.base}{bm.quote}-{expiry_suffix}.BINANCE"
        elif bm.linear:
            return f"{bm.base}{bm.quote}-PERP.BINANCE"
        elif bm.inverse:
            return f"{bm.base}{bm.quote}-PERP.BINANCE"
            
    def load_markets(self):
        market = self.api.load_markets()
        for k,v in market.items():
            try:
                v_json = orjson.dumps(v)
                v = msgspec.json.decode(v_json, type=BinanceMarket)
                
                if v.spot or v.future or v.linear or v.inverse:
                    symbol = self.parse_symbol(v)
                    self.market[symbol] = v
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

if __name__ == "__main__":
    bm = BinanceExchangeManager()
    bm.load_markets()
    print(bm.market.keys())
