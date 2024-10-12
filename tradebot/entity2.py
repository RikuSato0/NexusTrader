import socket
import ccxt

from typing import Dict
from decimal import Decimal
from dataclasses import dataclass, field
from collections import defaultdict

from tradebot.entity import Order


import redis
import orjson

class RedisPool:
    def __init__(self):
        if self._is_in_docker():
            self.pool = redis.ConnectionPool(host='redis', db=0, password='password')
        else:
            self.pool = redis.ConnectionPool(host='localhost', port=6379, db=0, password='password')
    
    def _is_in_docker(self):
        try:
            socket.gethostbyname('redis')
            return True
        except socket.gaierror:
            return False
    
    def get_client(self) -> redis.Redis:
        return redis.Redis(connection_pool=self.pool)
    
    def close(self):
        self.pool.close()


@dataclass
class Asset:
    free: Decimal = field(default=Decimal(0))
    borrowed: Decimal = field(default=Decimal(0))
    locked: Decimal = field(default=Decimal(0))
    total: Decimal = field(default=Decimal(0))
    
    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            free=Decimal(data['free']),
            borrowed=Decimal(data['borrowed']),
            locked=Decimal(data['locked']),
            total=Decimal(data['total'])
        )
    
    def to_dict(self) -> Dict:
        return {
            'free': str(self.free),
            'borrowed': str(self.borrowed),
            'locked': str(self.locked),
            'total': str(self.total)
        }
    


@dataclass
class Account:
    user_id: str
    account_type: str
    exchange_id: str
    redis_client: redis.Redis
    assets: Dict[str, Asset] = field(default_factory=lambda: defaultdict(Asset))

    def __post_init__(self):
        self.key = f"{self.exchange_id}:{self.user_id}:account:{self.account_type}"
    
    def update_asset(self, order: Order, markets: Dict):
        market = markets[order.symbol]
        base = market['base']
        quote = market['quote']
        symbol_type = market['type']
        if symbol_type != 'spot':
            raise ValueError(f"Symbol type {symbol_type} is not supported")
        exchange = order.exchange
        
        match exchange:
            case "binance":
                pass
            
            case "okx":
                pass
            
            case "bybit":
                pass

    




