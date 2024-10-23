import json
import time
from statistics import mean, stdev

import orjson
import msgspec


LOAD_WITH_FORMAT = False


class User(msgspec.Struct):
    id: int
    name: str
    email: str
    age: int
    is_active: bool
    score: float


def generate_test_data(n):
    return [
        json.dumps(
            {
                "id": i,
                "name": f"User{i}",
                "email": f"user{i}@example.com",
                "age": 20 + (i % 50),
                "is_active": i % 2 == 0,
                "score": round(i / 10, 2),
            }
        )
        for i in range(n)
    ]


def test_orjson(data):
    if LOAD_WITH_FORMAT:
        return [User(**orjson.loads(item)) for item in data]
    else:
        return [orjson.loads(item) for item in data]


def test_msgspec(data):
    if LOAD_WITH_FORMAT:
        decoder = msgspec.json.Decoder(User)
    else:
        decoder = msgspec.json.Decoder()

    return [decoder.decode(item) for item in data]


def run_benchmark(n_messages, n_iterations):
    test_data = generate_test_data(n_messages)

    # JIT Warm-up ?
    # 在正式计时前运行一些迭代，以确保 JIT 优化已经应用
    # for _ in range(1000):
    #     test_orjson(test_data[:10])
    #     test_msgspec(test_data[:10], msgspec_decoder)

    orjson_times = []
    msgspec_times = []

    for _ in range(n_iterations):
        start = time.perf_counter()
        test_orjson(test_data)
        orjson_times.append(time.perf_counter() - start)

        start = time.perf_counter()
        test_msgspec(test_data)
        msgspec_times.append(time.perf_counter() - start)

    print(f"orjson:  {mean(orjson_times):.6f} ± {stdev(orjson_times):.6f} seconds")
    print(f"msgspec: {mean(msgspec_times):.6f} ± {stdev(msgspec_times):.6f} seconds")


def test1():
    dict_ = json.dumps(
        {
            "id": 1,
            "name": f"User{1}",
            "email": f"user{1}@example.com",
            "age": 20 + (1 % 50),
            "is_active": 1 % 2 == 0,
            "score": round(1 / 10, 2),
        }
    )
    msgspec_decoder = msgspec.json.Decoder(User)

    data = msgspec_decoder.decode(dict_)
    print(type(data))
    print(data)
    print(data.age)


if __name__ == "__main__":
    N_MESSAGES = 500
    N_ITERATIONS = 100000

    print(
        f"LOAD_WITH_FORMAT: {LOAD_WITH_FORMAT}, Benchmarking with {N_MESSAGES} messages, {N_ITERATIONS} iterations:"
    )
    run_benchmark(N_MESSAGES, N_ITERATIONS)
