import pytest

from collections import defaultdict

from tradebot.entity import Account, RedisPool, Context, PositionDict


@pytest.fixture
def redis_manager():
    redis_manager = RedisPool()
    yield redis_manager
    db = redis_manager.get_client()
    db.flushall()
    db.close()



def test_account(redis_manager):
    # delet all data in redis
    db = redis_manager.get_client()
    # db.flushall()
    
    spot = Account('account_1','spot',db)
    assert spot.USDT == 0
    assert spot.BTC == 0
    spot.USDT = 100
    assert spot.USDT == 100
    assert spot.BNB == 0
    assert spot['USDT'] == 100
    assert spot['BNB'] == 0
    spot.BNB = 10
    assert spot.BNB == 10
    assert spot['BNB'] == 10
    
    del spot
    spot = Account('account_1','spot',db)
    assert spot.USDT == 100
    assert spot.BNB == 10
    
    future = Account('account_1','future',db)
    future.FDUSD = 100
    assert future.FDUSD == 100
    assert future.BTC == 0
    future.BTC = 10
    assert future.BTC == 10
    future.FDUSD = 200
    assert future.FDUSD == 200
    
    del future
    future = Account('account_1','future',db)
    assert future.FDUSD == 200

    #test for account_2 account
    spot = Account('account_2','spot',db)
    spot.USDT = 100
    assert spot.USDT == 100
    assert spot.BNB == 0
    spot.BNB = 10
    assert spot.BNB == 10
    
    del spot
    spot = Account('account_2','spot',db)
    assert spot.USDT == 100
    assert spot.BNB == 10
    
    future = Account('account_2','future',db)
    future.FDUSD = 100
    assert future.FDUSD == 100
    assert future.BTC == 0
    future.BTC = 10
    assert future.BTC == 10
    future.FDUSD = 200
    assert future.FDUSD == 200
    
    del future
    future = Account('account_2','future',db)
    assert future.FDUSD == 200
    assert future.BTC == 10


def test_position_dict(redis_manager):
    db = redis_manager.get_client()
    
    position_dict = PositionDict('account_1',db)
    
    position_dict.update('BTC/USDT', 10, 65200)
    position_dict.update('ETH/USDT', 10, 2847)
    assert position_dict['BTC/USDT'].amount == 10
    assert position_dict['BTC/USDT'].last_price == 65200
    assert position_dict['ETH/USDT'].amount == 10
    
    position_dict.update('BTC/USDT', -5, 65300)
    assert position_dict['BTC/USDT'].amount == 5
    
    position_dict.update('ETH/USDT', -2, 65400)
    assert position_dict['ETH/USDT'].amount == 8
    
    del position_dict   
    
    position_dict = PositionDict('account_1',db)
    
    assert position_dict['BTC/USDT'].amount == 5
    
    position_dict.update('BTC/USDT', -5, 65300)

    assert "BTC/USDT" not in position_dict
    
    position_dict.update('BTC/USDT:USDT', 10, 65200)
    position_dict.update('BTC/USDT:USDT', -5, 65300)
    
    assert position_dict['BTC/USDT:USDT'].amount == 5
    
    position_dict.update('SOL/USDT', 10, 40)
    position_dict.update('ENJ/USDT', 10, 1.5)
    position_dict.update('ENJ/USDT:USDT', -5, 1.6)
    position_dict.update('SOL/USDT:USDT', -5, 41)
    
    assert "SOL/USDT" in position_dict.spot
    assert "ENJ/USDT" in position_dict.spot
    assert "SOL/USDT:USDT" not in position_dict.spot
    assert "ENJ/USDT:USDT" not in position_dict.spot
    assert "SOL/USDT" not in position_dict.future
    assert "ENJ/USDT" not in position_dict.future
    assert "SOL/USDT:USDT" in position_dict.future
    assert "ENJ/USDT:USDT" in position_dict.future
    
    assert "SOL/USDT" in position_dict
    assert "ENJ/USDT" in position_dict
    assert "SOL/USDT:USDT" in position_dict
    assert "ENJ/USDT:USDT" in position_dict


def test_context(redis_manager):
    
    db = redis_manager.get_client()
    db.flushall()
    context = Context('account_1',db)
    
    context.spot_account.USDT = 100
    context.spot_account.BNB = 10
    context.spot_account.BTC = 5
    context.spot_account.ETH = 2
    context.linear_account.FDUSD = 100
    context.linear_account.BTC = 10
    
    assert context.spot_account.USDT == 100
    assert context.spot_account.BNB == 10
    assert context.spot_account.BTC == 5
    assert context.spot_account.ETH == 2
    assert context.spot_account.FDUSD == 0
    assert context.spot_account.USDC == 0
    assert context.spot_account['USDT'] == 100
    assert context.spot_account['BNB'] == 10
    assert context.spot_account['BTC'] == 5
    assert context.spot_account['ETH'] == 2
    assert context.spot_account['FDUSD'] == 0
    assert context.spot_account['USDC'] == 0
    assert context.linear_account.FDUSD == 100
    assert context.linear_account.BTC == 10
    assert context.linear_account.USDT == 0
    assert context.linear_account.BNB == 0
    assert context.linear_account.ETH == 0
    assert context.linear_account.USDC == 0
    assert context.linear_account['FDUSD'] == 100
    assert context.linear_account['BTC'] == 10
    assert context.linear_account['USDT'] == 0
    assert context.linear_account['BNB'] == 0
    assert context.linear_account['ETH'] == 0
    assert context.linear_account['USDC'] == 0
    
    del context
    
    context = Context('account_1',db)
    
    assert context.spot_account.USDT == 100
    assert context.spot_account.BNB == 10
    assert context.spot_account.BTC == 5
    assert context.spot_account.ETH == 2
    assert context.spot_account.FDUSD == 0
    assert context.spot_account.USDC == 0
    assert context.linear_account.FDUSD == 100
    assert context.linear_account.BTC == 10
    assert context.linear_account.USDT == 0
    assert context.linear_account.BNB == 0
    assert context.linear_account.ETH == 0
    assert context.linear_account.USDC == 0
    
    context.level_time = defaultdict(int)
    context.level_time['BTC/USDT'] = 10
    context.level_time['ETH/USDT'] = 20
    assert context.level_time['BTC/USDT'] == 10
    assert context.level_time['ETH/USDT'] == 20

    context.position.update('BTC/USDT', 10, 65200)
    context.position.update('ETH/USDT', 10, 2847)
    assert context.position['BTC/USDT'].amount == 10
    assert context.position['BTC/USDT'].last_price == 65200
    assert context.position['ETH/USDT'].amount == 10
    assert context.position['ETH/USDT'].last_price == 2847
    
    context.position.update('BTC/USDT', -5, 65300)
    assert context.position['BTC/USDT'].amount == 5
    context.position.update('ETH/USDT', -2, 65400)
    assert context.position['ETH/USDT'].amount == 8
    
    del context
    
    context = Context('account_1',db)
    
    assert context.position['BTC/USDT'].amount == 5
    assert context.position['ETH/USDT'].amount == 8
    
    context.position.update('BTC/USDT', -5, 65300)
    context.position.update('ETH/USDT', -8, 65400)
    
    assert "BTC/USDT" not in context.position
    assert "ETH/USDT" not in context.position
    
    