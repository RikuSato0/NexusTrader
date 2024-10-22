from typing import Any, Dict
from tradebot.base import ExchangeManager


class OkxExchangeManager(ExchangeManager):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.market_id = None

    async def load_markets(self):
        await super().load_markets()
        self._get_market_id()

    def _get_market_id(self):
        self.market_id = {}
        if not self.market:
            raise ValueError(
                "Market data not loaded, please call `load_markets()` first"
            )
        for _, v in self.market.items():
            self.market_id[v["id"]] = v
