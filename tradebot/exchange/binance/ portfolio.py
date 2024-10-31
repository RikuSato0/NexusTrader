import redis
import msgspec
from decimal import Decimal
from typing import Dict
from tradebot.types import Asset
from tradebot.constants import AccountType
from tradebot.entity import RedisPool
from tradebot.exchange.binance import BinanceAccountType
from tradebot.exchange.okx import OkxAccountType


class Account:
    """
    Only store the asset in that account

    spot = Account(BinanceAccountType.SPOT)
    spot["BTC"].update_free()
    spot["BTC"].update_borrowed()  # only for margin account
    spot["BTC"].update_locked()  # only for limit unfulfilled order

    spot["BTC"].total
    spot["BTC"].free
    spot["BTC"].borrowed
    spot["BTC"].locked

    How to store the asset in the account?

    > Each strategy has multiple types of accounts

    binance spot, binance margin, binance usdm futures, binance coinm futures, Portfolio margin account has (margin, usdm futures, coinm futures)
    okx only has one account

    > Each account is a dictionary of assets (Asset class)

    We can get asset by symbol e.g., spot["BTC"], spot["ETH"], spot["USDT"]

    > Same strategy and same account type can belong to different users

    We use API_KEY and SECRET to generate the user_id of the account
    """

    def __init__(
        self,
        account_type: AccountType,
        strategy_id: str,
        user_id: str,
        redis_client: redis.Redis,
    ):
        self._r = redis_client
        self._key = (
            f"strategy:{strategy_id}:user_id:{user_id}:account_type:{account_type}"
        )
        self._assets: Dict[str, Asset] = {}
        self._load_account()

    def _encode(self, asset: Asset) -> bytes:
        return msgspec.json.encode(asset)

    def _decode(self, data: bytes) -> Asset:
        return msgspec.json.decode(data, type=Asset)

    def _load_account(self):
        """
        Load all assets from Redis into the local dictionary.
        """
        data = self._r.hgetall(self._key)
        for symbol, asset_data in data.items():
            asset = self._decode(asset_data)
            self._assets[symbol.decode('utf-8')] = asset

    def _save_asset(self, symbol: str, asset: Asset):
        """
        Save a single asset to Redis.
        """
        encoded = self._encode(asset)
        self._r.hset(self._key, symbol, encoded)

    def __getitem__(self, symbol: str) -> Asset:
        return self._assets[symbol]

    def __setitem__(self, symbol: str, asset: Asset):
        self._assets[symbol] = asset
        self._save_asset(symbol, asset)

    def __delitem__(self, symbol: str):
        if symbol in self._assets:
            del self._assets[symbol]
            self._r.hdel(self._key, symbol)

    def __contains__(self, symbol: str) -> bool:
        return symbol in self._assets

    def keys(self):
        return self._assets.keys()

    def items(self):
        return self._assets.items()

    def __iter__(self):
        return iter(self._assets)

    def __len__(self):
        return len(self._assets)



def main():
    pool = RedisPool()
    r = pool.get_client()
    
    bnc_spot = Account(
        account_type=BinanceAccountType.SPOT,
        strategy_id="strategy1",
        user_id="user1",
        redis_client=r,
    )
    
    bnc_spot["BTC"].update_free(Decimal("1.0"))
    assert bnc_spot["BTC"].free == Decimal("1.0")
    assert bnc_spot["BTC"].total == Decimal("1.0")
    assert bnc_spot["BTC"].locked == Decimal("0.0")
    assert bnc_spot["BTC"].borrowed == Decimal("0.0")
    bnc_spot["BTC"] = bnc_spot["BTC"]
    
    del bnc_spot
    
    bnc_spot = Account(
        account_type=BinanceAccountType.SPOT,
        strategy_id="strategy1",
        user_id="user1",
        redis_client=r,
    )

    assert bnc_spot["BTC"].free == Decimal("1.0")
    
if __name__ == "__main__":
    main()
    
    
        
        
        
    
    
        
    
    
    
