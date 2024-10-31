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
    spot["BTC"].update_borrowed() # only for margin account
    spot["BTC"].update_locked() # only for limit unfulfilled order

    spot["BTC"].total
    spot["BTC"].free
    spot["BTC"].borrowed
    spot["BTC"].locked

    how to store the asset in the account?

    > each strategy has multiple types of accounts

    binance spot, binance margin, binance usdm futures, binance coinm futures, Portfolio margin account has (margin, usdm futures, coinm futures)
    okx only has one account

    > each account is a dictionary of assets (Asset class)

    we can get asset by symbol eg. spot["BTC"], spot["ETH"], spot["USDT"]

    > same strategy and same account type can belongs to different users

    we using API_KEY and SECRET to generate the user_id of the account
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
        self._load_account()
        
    def __setattr__(self, asset, value):
        super().__setattr__(asset, value)
        if asset not in ["_r", "_key"]:
            self._r.hset(self._key, asset, self._encode(value))
    
    def __getattr__(self, asset):
        if asset not in ["_r", "_key"]:
            data = self._r.hget(self._key, asset)
            if data is None:
                return Asset(asset)
            return self._decode(data)
        raise AttributeError(f"'{self.__class__.__name__}' object has no Asset: '{asset}'")
        
        
    def _encode(self, asset: Asset) -> bytes:
        return msgspec.json.encode(asset)
    
    def _decode(self, data: bytes) -> Asset:
        return msgspec.json.decode(data, type=Asset)
    
    def __getitem__(self, asset: str) -> Asset:
        return getattr(self, asset)
    
    def __setitem__(self, asset: str, value: Asset):
        setattr(self, asset, value)
    
    def _load_account(self):
        for asset, value in self._r.hgetall(self._key).items():
            setattr(self, asset.decode(), self._decode(value))
    
    def update_free(self, asset: str, amount: Decimal):
        asset_obj = self[asset]
        asset_obj._update_free(amount)
        self[asset] = asset_obj
    
    def update_locked(self, asset: str, amount: Decimal):
        asset_obj = self[asset]
        asset_obj._update_locked(amount)
        self[asset] = asset_obj
    
    def update_borrowed(self, asset: str, amount: Decimal):
        asset_obj = self[asset]
        asset_obj._update_borrowed(amount)
        self[asset] = asset_obj



def main():
    pool = RedisPool()
    r = pool.get_client()
    r.flushall()
    bnc_spot = Account(
        account_type=BinanceAccountType.SPOT,
        strategy_id="strategy1",
        user_id="user1",
        redis_client=r,
    )
    
    bnc_spot.update_free("BTC", Decimal("1.0"))
    assert bnc_spot["BTC"].free == Decimal("1.0")
    assert bnc_spot["BTC"].total == Decimal("1.0")
    assert bnc_spot["BTC"].locked == Decimal("0.0")
    assert bnc_spot["BTC"].borrowed == Decimal("0.0")
    
    del bnc_spot
    
    bnc_spot = Account(
        account_type=BinanceAccountType.SPOT,
        strategy_id="strategy1",
        user_id="user1",
        redis_client=r,
    )
    
    bnc_future = Account(
        account_type=BinanceAccountType.USD_M_FUTURE,
        strategy_id="strategy1",
        user_id="user1",
        redis_client=r,
    )

    assert bnc_spot["BTC"].free == Decimal("1.0")
    
    bnc_future.update_borrowed("BTC", Decimal("3.0"))
    
    assert bnc_future["BTC"].borrowed == Decimal("3.0")
    assert bnc_future["BTC"].total == Decimal("3.0")
    
    del bnc_future
    
    bnc_future = Account(
        account_type=BinanceAccountType.USD_M_FUTURE,
        strategy_id="strategy1",
        user_id="user1",
        redis_client=r,
    )
    
    assert bnc_future["BTC"].borrowed == Decimal("3.0")
    assert bnc_future["BTC"].total == Decimal("3.0")
    


    
if __name__ == "__main__":
    main()
    
    
        
        
        
    
    
        
    
    
    
