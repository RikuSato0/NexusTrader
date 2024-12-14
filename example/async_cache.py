import asyncio
import time
from decimal import Decimal
from tradebot.constants import OrderStatus, ExchangeType
from tradebot.types import Order, OrderType, OrderSide
from tradebot.core.cache import AsyncCache
from tradebot.core.entity import RedisClient, TaskManager

async def test_async_cache():
    # Initialize test parameters
    strategy_id = "test_strategy"
    user_id = "test_user"

    # Create test orders
    test_orders = [
        Order(
            exchange=ExchangeType.BYBIT,
            id=f"order_{i}",
            symbol="BTCUSDT-PERP.BYBIT",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            price=30000,
            amount=Decimal("1"),
            status=OrderStatus.ACCEPTED,
            timestamp=int(time.time() * 1000)
        ) for i in range(3)
    ]
    
    task_manager = TaskManager(asyncio.new_event_loop())
    # Initialize cache with shorter sync interval for testing
    cache = AsyncCache(
        strategy_id=strategy_id,
        user_id=user_id,
        task_manager=task_manager,
        sync_interval=1,  # 2 seconds for testing
        expire_time=5    # 60 seconds for testing
    )
    
    try:
        # Start background tasks
        await cache.start()
        
        print("Testing order initialization...")
        for order in test_orders:
            cache._order_initialized(order)
            
        # Verify orders are in memory
        open_orders = await cache.get_open_orders(exchange=ExchangeType.BYBIT)
        print(f"Open orders after initialization: {open_orders}")
        
        # Test order retrieval
        order = await cache.get_order("order_0")
        print(f"Retrieved order: {order}")
        
        # Test symbol orders
        symbol_orders = await cache.get_symbol_orders("BTCUSDT-PERP.BYBIT")
        print(f"Symbol orders: {symbol_orders}")
        
        # Test order status update
        updated_order = test_orders[0]
        updated_order.status = OrderStatus.FILLED
        cache._order_status_update(updated_order)
        
        # Verify open orders after update
        open_orders = await cache.get_open_orders(exchange=ExchangeType.BYBIT)
        print(f"Open orders after status update: {open_orders}")
        
        # Wait for sync to Redis
        print("Waiting for sync to Redis...")
        await asyncio.sleep(10)
        
        # Test retrieval from Redis
        order = await cache.get_order("order_0")
        print(f"Order retrieved after sync: {order}")
        
    finally:
        # Cleanup
        await cache.close()
        await task_manager.cancel()
        
async def main():
    # Clear Redis before testing
    redis_client = RedisClient.get_client()
    redis_client.flushall()
    
    print("Starting AsyncCache tests...")
    await test_async_cache()
    print("Tests completed.")

if __name__ == "__main__":
    asyncio.run(main())
