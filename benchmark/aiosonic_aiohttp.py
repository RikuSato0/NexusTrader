import asyncio
import time
from decimal import Decimal

import aiohttp
import aiosonic

# 测试参数
NUM_REQUESTS = 100

TEST_URL = "https://httpbin.org/post"  # 用于测试POST请求的URL


async def aio_request(session: aiohttp.ClientSession, index: int):
    async with session.post(TEST_URL, json={"key": "value"}) as response:
        print(f"Aiohttp: Request {index} completed, status: {response.status}")
        return response.status


async def aiohttp_test():
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(NUM_REQUESTS):
            tasks.append(aio_request(session, i))

        start_time = time.perf_counter()
        await asyncio.gather(*tasks)
        end_time = time.perf_counter()

    return end_time - start_time


async def aiosonic_request(client: aiosonic.HTTPClient, index: int):
    response = await client.post(TEST_URL, json={"key": "value"})
    print(f"Aiosonic: Request {index} completed, status: {response.status_code}")
    return response.status_code


async def aiosonic_test():
    connector = aiosonic.TCPConnector()
    client = aiosonic.HTTPClient(connector)
    tasks = []
    for i in range(NUM_REQUESTS):
        tasks.append(aiosonic_request(client, i))

    start_time = time.perf_counter()
    await asyncio.gather(*tasks)
    end_time = time.perf_counter()

    return end_time - start_time


async def run_benchmark():
    print(f"Running benchmark with {NUM_REQUESTS} requests")
    aiosonic_time = await aiosonic_test()
    print(f"aiosonic completed in {aiosonic_time:.2f} seconds")
    print(f"aiosonic requests per second: {NUM_REQUESTS / aiosonic_time:.2f}")

    aiohttp_time = await aiohttp_test()
    print(f"aiohttp completed in {aiohttp_time:.2f} seconds")
    print(f"aiohttp requests per second: {NUM_REQUESTS / aiohttp_time:.2f}")

    speedup = Decimal(aiohttp_time) / Decimal(aiosonic_time)
    print(f"aiosonic is {speedup:.2f}x faster than aiohttp")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
