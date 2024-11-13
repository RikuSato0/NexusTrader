from tradebot.entity import EventSystem
import numpy as np


from nautilus_trader.common.component import MessageBus
from nautilus_trader.common.component import LiveClock
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.common.config import MessageBusConfig, DatabaseConfig

latency = []

msgBus = MessageBus(
    trader_id=TraderId("tradebot-001"),
    clock=LiveClock(),
)


clock = LiveClock()

def test_func(msg):
    timestamp = clock.timestamp_ns()
    latency.append(timestamp - msg)
    

msgBus.register("test", test_func)

for i in range(100000):
    msgBus.send("test", clock.timestamp_ns())

mean = np.mean(latency)
std = np.std(latency)
print(f"mean: {mean}, std: {std}")

latency = []

def test_func2(msg):
    timestamp = clock.timestamp_ns()
    latency.append(timestamp - msg)

EventSystem.on("test2", test_func2)

for i in range(100000):
    EventSystem.emit("test2", clock.timestamp_ns())

mean = np.mean(latency)
std = np.std(latency)
print(f"mean: {mean}, std: {std}")
