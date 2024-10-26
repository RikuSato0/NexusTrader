import time
import random
from typing import List, Dict
from msgspec import Struct
from tradebot.ctypes import Kline as CKline
from dataclasses import dataclass


# 定义 Kline 结构
class Kline(Struct, gc=False):
    exchange: str
    symbol: str
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: int


# 新增: 使用原生 dataclass with slots=True
@dataclass(slots=True)
class KlineDataclass:
    exchange: str
    symbol: str
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: int


# 方法 1: 直接创建 Kline 对象
def method1(data: Dict) -> Kline:
    return Kline(
        exchange=data["exchange"],
        symbol=data["symbol"],
        interval=data["interval"],
        open=float(data["open"]),
        high=float(data["high"]),
        low=float(data["low"]),
        close=float(data["close"]),
        volume=float(data["volume"]),
        timestamp=int(data["timestamp"]),
    )


# 方法 2: 使用 ctypes
def method2(data: dict) -> CKline:
    return CKline(
        exchange=data["exchange"],
        symbol=data["symbol"],
        interval=data["interval"],
        open=float(data["open"]),
        high=float(data["high"]),
        low=float(data["low"]),
        close=float(data["close"]),
        volume=float(data["volume"]),
        timestamp=int(data["timestamp"]),
    )


# 方法 3: 使用原生 dataclass
def method3(data: Dict) -> KlineDataclass:
    return KlineDataclass(
        exchange=data["exchange"],
        symbol=data["symbol"],
        interval=data["interval"],
        open=float(data["open"]),
        high=float(data["high"]),
        low=float(data["low"]),
        close=float(data["close"]),
        volume=float(data["volume"]),
        timestamp=int(data["timestamp"]),
    )


# 生成测试数据
def generate_test_data(n: int) -> List[Dict]:
    return [
        {
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "interval": "1m",
            "open": random.uniform(30000, 40000),
            "high": random.uniform(30000, 40000),
            "low": random.uniform(30000, 40000),
            "close": random.uniform(30000, 40000),
            "volume": random.uniform(1, 100),
            "timestamp": int(time.perf_counter() * 1000),
        }
        for _ in range(n)
    ]


# 修改运行基准测试函数
def run_benchmark(n: int):
    test_data = generate_test_data(n)

    # 测试方法 1 - 创建
    start_time = time.perf_counter()
    method1_objects = [method1(data) for data in test_data]
    method1_create_time = time.perf_counter() - start_time

    # 测试方法 2 - 创建
    start_time = time.perf_counter()
    method2_objects = [method2(data) for data in test_data]
    method2_create_time = time.perf_counter() - start_time

    # 测试方法 3 - 创建
    start_time = time.perf_counter()
    method3_objects = [method3(data) for data in test_data]
    method3_create_time = time.perf_counter() - start_time

    # 测试方法 1 - 属性访问
    start_time = time.perf_counter()
    for obj in method1_objects:
        _ = obj.exchange + obj.symbol + obj.interval
        _ = obj.open + obj.high + obj.low + obj.close + obj.volume
        _ = obj.timestamp
    method1_access_time = time.perf_counter() - start_time

    # 测试方法 2 - 属性访问
    start_time = time.perf_counter()
    for obj in method2_objects:
        _ = obj.exchange + obj.symbol + obj.interval
        _ = obj.open + obj.high + obj.low + obj.close + obj.volume
        _ = obj.timestamp
    method2_access_time = time.perf_counter() - start_time

    # 测试方法 3 - 属性访问
    start_time = time.perf_counter()
    for obj in method3_objects:
        _ = obj.exchange + obj.symbol + obj.interval
        _ = obj.open + obj.high + obj.low + obj.close + obj.volume
        _ = obj.timestamp
    method3_access_time = time.perf_counter() - start_time

    print(f"Number of Klines processed: {n}")
    print(f"Method 1 (msgspec Struct) 创建时间: {method1_create_time:.4f} 秒")
    print(f"Method 2 (ctypes) 创建时间: {method2_create_time:.4f} 秒")
    print(f"Method 3 (dataclass with slots) 创建时间: {method3_create_time:.4f} 秒")
    print(f"Method 1 (msgspec Struct) 访问时间: {method1_access_time:.4f} 秒")
    print(f"Method 2 (ctypes) 访问时间: {method2_access_time:.4f} 秒")
    print(f"Method 3 (dataclass with slots) 访问时间: {method3_access_time:.4f} 秒")

    # 以下 method 后加上对应的括号
    print(
        f"Method 2 (ctypes) 相对 Method 1 (msgspec Struct) 的创建速度提升: {(method1_create_time / method2_create_time - 1) * 100:.2f}%"
    )
    print(
        f"Method 2 (ctypes) 相对 Method 1 (msgspec Struct) 的访问速度提升: {(method1_access_time / method2_access_time - 1) * 100:.2f}%"
    )
    print(
        f"Method 3 (dataclass with slots) 相对 Method 1 (msgspec Struct) 的创建速度提升: {(method1_create_time / method3_create_time - 1) * 100:.2f}%"
    )
    print(
        f"Method 3 (dataclass with slots) 相对 Method 1 (msgspec Struct) 的访问速度提升: {(method1_access_time / method3_access_time - 1) * 100:.2f}%"
    )


if __name__ == "__main__":
    for n in [1, 1000, 10000, 100000, 1000000]:
        print(f"\n--- 测试 {n} 个 Klines ---")
        run_benchmark(n)
