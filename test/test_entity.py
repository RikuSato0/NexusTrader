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
    
    assert "SOL/USDT" in position_dict
    assert "ENJ/USDT" in position_dict
    assert "SOL/USDT:USDT" in position_dict
    assert "ENJ/USDT:USDT" in position_dict


def test_context_save_new_varibale(redis_manager):
    
    db = redis_manager.get_client()
    db.flushall()
    
    context_new = Context('account_1',db)
    
    context_new.apple = 10
    
    assert context_new.apple == 10
    
    context_new.apple = 20
    
    assert context_new.apple == 20
    
    context_new.fruits = ['apple','banana','orange']
    
    assert "apple" in context_new.fruits
    assert "banana" in context_new.fruits
    assert "orange" in context_new.fruits
    assert "grape" not in context_new.fruits
    
    context_new.fruits_store = {
        'apple': 20,
        'banana': 10,
        'orange': 5
    }
    
    assert context_new.fruits_store['apple'] == 20
    assert context_new.fruits_store['banana'] == 10
    assert context_new.fruits_store['orange'] == 5
    
    del context_new
    
    context_new = Context('account_1',db)
    assert context_new.apple == 20
    assert "apple" in context_new.fruits
    assert "banana" in context_new.fruits
    assert "orange" in context_new.fruits
    assert "grape" not in context_new.fruits
    
    assert context_new.fruits_store['apple'] == 20
    assert context_new.fruits_store['banana'] == 10
    assert context_new.fruits_store['orange'] == 5
    



def test_context(redis_manager):
    
    db = redis_manager.get_client()
    db.flushall()
    context = Context('account_1',db)
    
    context.portfolio_account.USDT = 100
    context.portfolio_account.BNB = 10
    context.portfolio_account.BTC = 5
    context.portfolio_account.ETH = 2
    context.portfolio_account.FDUSD = 100
    
    assert context.portfolio_account.USDT == 100
    assert context.portfolio_account.BNB == 10
    assert context.portfolio_account.BTC == 5
    assert context.portfolio_account.ETH == 2
    assert context.portfolio_account.FDUSD == 100
    
    context.portfolio_account.USDT = 200
    context.portfolio_account.BNB = 20
    context.portfolio_account.BTC = 10
    context.portfolio_account.ETH = 5
    context.portfolio_account.FDUSD = 200
    
    assert context.portfolio_account.USDT == 200
    assert context.portfolio_account.BNB == 20
    assert context.portfolio_account.BTC == 10
    assert context.portfolio_account.ETH == 5
    assert context.portfolio_account.FDUSD == 200
    
    del context
    
    context = Context('account_1',db)
    
    assert context.portfolio_account.USDT == 200
    assert context.portfolio_account.BNB == 20
    assert context.portfolio_account.BTC == 10
    assert context.portfolio_account.ETH == 5
    assert context.portfolio_account.FDUSD == 200
    