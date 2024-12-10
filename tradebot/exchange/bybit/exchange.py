import ccxt
import orjson
import msgspec
from typing import Any, Dict
from tradebot.base import ExchangeManager
from tradebot.exchange.bybit.types import BybitMarket

class BybitExchangeManager(ExchangeManager):
    api: ccxt.bybit
    market = Dict[str, BybitMarket]
    market_id = Dict[str, BybitMarket]
    
    
    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        config["exchange_id"] = config.get("exchange_id", "bybit")
        super().__init__(config)

    def parse_symbol(self, bm: BybitMarket) -> str:
        if bm.spot:
            return f"{bm.base}{bm.quote}.BYBIT"
        elif bm.future:
            symbol = bm.symbol
            expiry_suffix = symbol.split("-")[-1]
            return f"{bm.base}{bm.quote}-{expiry_suffix}.BYBIT"
        elif bm.linear:
            return f"{bm.base}{bm.quote}-PERP.BYBIT"
        elif bm.inverse:
            return f"{bm.base}{bm.quote}-PERP.BYBIT"
    
    def load_markets(self):
        market = self.api.load_markets()
        for symbol, mkt in market.items():
            try:
                
                mkt_json = orjson.dumps(mkt)
                mkt = msgspec.json.decode(mkt_json, type=BybitMarket)
                if mkt.spot or mkt.future or mkt.linear or mkt.inverse:
                    symbol = self.parse_symbol(mkt)
                    mkt.symbol = symbol
                    self.market[symbol] = mkt
                    if mkt.type.value == "spot":
                        self.market_id[f"{mkt.id}_spot"] = symbol
                    elif mkt.linear:
                        self.market_id[f"{mkt.id}_linear"] = symbol
                    elif mkt.inverse:
                        self.market_id[f"{mkt.id}_inverse"] = symbol
                
            except Exception as e:
                print(f"Error: {e}, {symbol}, {mkt}")
                continue
