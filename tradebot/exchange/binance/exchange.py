import ccxt
import orjson
import msgspec
from typing import Any, Dict
from tradebot.base import ExchangeManager
from tradebot.exchange.binance.types import BinanceMarket
from tradebot.types import InstrumentId

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
                    v.symbol = symbol
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

def check():
    bnc = BinanceExchangeManager()
    market = bnc.market
    
    for symbol, mkt in market.items():
        instrument_id = InstrumentId.from_str(symbol)
        if mkt.subType:
            assert instrument_id.type == mkt.subType
        else:
            assert instrument_id.type == mkt.type
    
    print("All checks passed")

if __name__ == "__main__":
    check()
    
    
    
