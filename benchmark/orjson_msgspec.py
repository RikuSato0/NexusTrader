import json
import time
from statistics import mean, stdev

import orjson
import msgspec


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
    for item in data:
        orjson.loads(item)


def test_msgspec(data):
    decoder = msgspec.json.Decoder(User)
    for item in data:
        decoder.decode(item)


def run_benchmark(n_messages, n_iterations):
    test_data = generate_test_data(n_messages)

    orjson_times = []
    msgspec_times = []

    for _ in range(n_iterations):
        # Test orjson
        start = time.time()
        test_orjson(test_data)
        end = time.time()
        orjson_times.append(end - start)

        # Test msgspec
        start = time.time()
        test_msgspec(test_data)
        end = time.time()
        msgspec_times.append(end - start)

    print(f"orjson:  {mean(orjson_times):.6f} ± {stdev(orjson_times):.6f} seconds")
    print(f"msgspec: {mean(msgspec_times):.6f} ± {stdev(msgspec_times):.6f} seconds")


if __name__ == "__main__":
    N_MESSAGES = 1000
    N_ITERATIONS = 100

    print(f"Benchmarking with {N_MESSAGES} messages, {N_ITERATIONS} iterations:")
    run_benchmark(N_MESSAGES, N_ITERATIONS)
