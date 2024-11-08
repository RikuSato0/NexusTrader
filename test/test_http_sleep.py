import asyncio
import time
import aiohttp
from tradebot.base import Clock


async def slow_external_request():
    """模拟一个耗时的外部请求"""
    async with aiohttp.ClientSession() as session:
        try:
            # 模拟一个需要300ms的请求
            await asyncio.sleep(3)
            return {"data": "some data"}
        except Exception as e:
            print(f"Request error: {e}")


async def strategy_callback(timestamp):
    """策略回调函数"""
    print(f"[{time.strftime('%H:%M:%S.%f')[:-3]}] 开始执行策略回调")

    # 执行耗时的外部请求
    result = await slow_external_request()

    print(f"[{time.strftime('%H:%M:%S.%f')[:-3]}] 策略回调执行完成")


async def main():
    # 创建一个tick_size为50ms的Clock
    clock = Clock(tick_size=0.05)  # 50ms

    # 注册策略回调
    clock.add_tick_callback(strategy_callback)

    # 运行时钟
    await clock.run()


# 运行示例
if __name__ == "__main__":
    asyncio.run(main())
