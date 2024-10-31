import pytest
from decimal import Decimal
from tradebot.exchange.binance import BinanceAccountType
from tradebot.exchange.okx import OkxAccountType
from tradebot.entity2 import Account, RedisPool


@pytest.fixture
def redis_manager():
    redis_manager = RedisPool()
    yield redis_manager
    db = redis_manager.get_client()
    db.flushall()
    db.close()

def test_account(redis_manager):
    r = redis_manager.get_client()
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
    
    okx = Account(
        account_type=OkxAccountType.LIVE,
        strategy_id="strategy1",
        user_id="user1",
        redis_client=r,
    )
    
    okx.set_value("BTC", free=Decimal("1.0"), borrowed=Decimal("2.0"), locked=Decimal("3.0"))
    
    assert okx["BTC"].free == Decimal("1.0")
    assert okx["BTC"].borrowed == Decimal("2.0")
    assert okx["BTC"].locked == Decimal("3.0")
    assert okx["BTC"].total == Decimal("4.0")
    
    del okx
    
    okx = Account(
        account_type=OkxAccountType.LIVE,
        strategy_id="strategy1",
        user_id="user1",
        redis_client=r,
    )
    
    assert okx["BTC"].free == Decimal("1.0")
    assert okx["BTC"].borrowed == Decimal("2.0")
    assert okx["BTC"].locked == Decimal("3.0")
    assert okx["BTC"].total == Decimal("4.0")
    
    okx2 = Account(
        account_type=OkxAccountType.LIVE,
        strategy_id="strategy2",
        user_id="user1",
        redis_client=r,
    )
    
    okx2.update_free("ETH", Decimal("1.0"))
    
    assert okx2["ETH"].free == Decimal("1.0")
    assert okx2["ETH"].total == Decimal("1.0")
    assert okx2["ETH"].locked == Decimal("0.0")
