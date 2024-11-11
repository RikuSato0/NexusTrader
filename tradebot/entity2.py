import socket
import redis
import msgspec
from typing import Dict, Set
from decimal import Decimal
from tradebot.constants import AccountType
from tradebot.types import Asset, Order


class RedisPool:
    def __init__(self):
        if self._is_in_docker():
            self.pool = redis.ConnectionPool(host="redis", db=0, password="password")
        else:
            self.pool = redis.ConnectionPool(
                host="localhost", port=6379, db=0, password="password"
            )

    def _is_in_docker(self):
        try:
            socket.gethostbyname("redis")
            return True
        except socket.gaierror:
            return False

    def get_client(self) -> redis.Redis:
        return redis.Redis(connection_pool=self.pool)

    def close(self):
        self.pool.close()


class Account:
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
    
    def set_value(self, asset: str, free: Decimal = None, borrowed: Decimal = None, locked: Decimal = None):
        asset_obj = self[asset]
        asset_obj._set_value(free, borrowed, locked)
        self[asset] = asset_obj
