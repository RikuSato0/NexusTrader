from nautilus_trader.common.component import MessageBus
from nautilus_trader.common.component import LiveClock
from nautilus_trader.model.identifiers import TraderId

from nautilus_trader.core.nautilus_pyo3 import HttpClient # noqa
from nautilus_trader.core.nautilus_pyo3 import HttpMethod # noqa
from nautilus_trader.core.nautilus_pyo3 import HttpResponse # noqa

from nautilus_trader.core.nautilus_pyo3 import WebSocketClient # noqa
from nautilus_trader.core.nautilus_pyo3 import WebSocketClientError # noqa
from nautilus_trader.core.nautilus_pyo3 import WebSocketConfig # noqa



def usage():
    clock = LiveClock()

    def handler1(msg):
        print(f"Received message: {msg}")
    def handler2(msg):
        print(f"Received message: {msg}")

    def handler3(msg):
        print(f"Received message: {msg}")

    msgbus = MessageBus(
        trader_id=TraderId("TESTER-001"),
        clock=clock,
    )

    msgbus.subscribe(topic = "order", handler=handler1)
    msgbus.subscribe(topic = "order", handler=handler2)
    msgbus.subscribe(topic = "order", handler=handler3)

    msgbus.publish(topic="order", msg=clock.timestamp_ns())
    
    
    msgbus.register(endpoint="pos", handler=handler1)
    msgbus.register(endpoint="pos1", handler=handler1)
    msgbus.register(endpoint="pos2", handler=handler1)
    

    
    msgbus.send(endpoint="pos", msg=clock.timestamp_ns())
    msgbus.send(endpoint="pos1", msg=clock.timestamp_ns())
    msgbus.send(endpoint="pos2", msg=clock.timestamp_ns())
    
    
    
    

if __name__ == "__main__":
    usage()
