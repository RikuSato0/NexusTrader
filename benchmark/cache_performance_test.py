import time
import uuid
import numpy as np
from decimal import Decimal
from typing import List, Tuple
import msgspec
from tradebot.entity import Cache
from tradebot.types import Order
from tradebot.constants import OrderStatus, OrderSide, OrderType
from tradebot.exchange.binance import BinanceAccountType

def create_sample_order(symbol: str = "BTC/USDT") -> Order:
    """Create a sample order for testing"""
    return Order(
        exchange="binance",
        id=int(uuid.uuid4()),
        client_order_id=str(uuid.uuid4()),
        timestamp=int(time.time() * 1000),
        symbol=symbol,
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        status=OrderStatus.ACCEPTED,
        price=50000.0,
        amount=Decimal("0.1"),
        filled=Decimal("0"),
        remaining=Decimal("0.1")
    )

class CachePerformanceTester:
    def __init__(self):
        self.cache = Cache(
            account_type=BinanceAccountType.SPOT,
            strategy_id="perf_test",
            user_id="test_user"
        )

    def _calculate_stats(self, times: List[float]) -> Tuple[float, float, float, float, float]:
        """Calculate statistics for a list of times (in seconds)"""
        times_ms = np.array(times) * 1000  # Convert to milliseconds
        return (
            np.mean(times_ms),    # average
            np.std(times_ms),     # standard deviation
            np.median(times_ms),  # median
            np.percentile(times_ms, 95),  # 95th percentile
            np.percentile(times_ms, 99)   # 99th percentile
        )

    def test_single_operations(self, num_orders: int = 1000):
        """测试单线程下的基本操作性能，记录每个操作的具体耗时"""
        print(f"\n详细性能测试 ({num_orders} 订单):")
        
        init_times = []
        query_times = []
        update_times = []
        orders: List[Order] = []

        # 测试初始化性能
        for _ in range(num_orders):
            order = create_sample_order()
            raw = msgspec.json.encode(order)
            order = msgspec.json.decode(raw, type=Order)
            
            
            start_time = time.time()
            self.cache.order_initialized(order)
            init_times.append(time.time() - start_time)
            orders.append(order)

        # 测试查询性能
        for order in orders:
            start_time = time.time()
            self.cache.get_order(order.id)
            query_times.append(time.time() - start_time)

        # 测试更新性能
        for order in orders:
            order.status = OrderStatus.FILLED
            start_time = time.time()
            self.cache.order_status_update(order)
            update_times.append(time.time() - start_time)

        # 计算并输出统计信息
        for op_name, times in [
            ("初始化订单", init_times),
            ("更新订单", update_times),
            ("查询订单", query_times)
        ]:
            avg, std, median, p95, p99 = self._calculate_stats(times)
            print(f"\n{op_name}统计信息:")
            print(f"  平均时间: {avg:.3f} ms")
            print(f"  标准差: {std:.3f} ms")
            print(f"  中位数: {median:.3f} ms")
            print(f"  95%分位: {p95:.3f} ms")
            print(f"  99%分位: {p99:.3f} ms")

def main():
    tester = CachePerformanceTester()
    tester.test_single_operations(num_orders=1000)

if __name__ == "__main__":
    main()
