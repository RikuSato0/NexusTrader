from nautilus_trader.common.component import MessageBus
from nautilus_trader.common.component import LiveClock
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.core.uuid import UUID4

from nautilus_trader.core.nautilus_pyo3 import HttpClient # noqa
from nautilus_trader.core.nautilus_pyo3 import HttpMethod # noqa
from nautilus_trader.core.nautilus_pyo3 import HttpResponse # noqa

from nautilus_trader.core.nautilus_pyo3 import WebSocketClient # noqa
from nautilus_trader.core.nautilus_pyo3 import WebSocketClientError # noqa
from nautilus_trader.core.nautilus_pyo3 import WebSocketConfig # noqa
from nautilus_trader.core.nautilus_pyo3 import hmac_signature, rsa_signature, ed25519_signature # noqa



def usage():
    
    print(UUID4().value)
    print(UUID4().value)
    print(UUID4().value)
    
    uuid_to_order_id = {}
    
    uuid = UUID4()
    
    order_id = "123456"
    
    uuid_to_order_id[uuid] = order_id
    
    print(uuid_to_order_id)
    
    clock = LiveClock()
    print(type(clock.timestamp_ms()))
    
    print(clock.utc_now().isoformat(timespec='milliseconds').replace('+00:00', 'Z')) 

    def handler1(msg):
        print(f"Received message: {msg} - handler1")
        
        
    def handler2(msg):
        print(f"Received message: {msg} - handler2")

    def handler3(msg):
        print(f"Received message: {msg} - handler3")

    msgbus = MessageBus(
        trader_id=TraderId("TESTER-001"),
        clock=clock,
    )

    msgbus.subscribe(topic = "BINANCE.order", handler=handler1)
    msgbus.subscribe(topic = "BYBIT.order", handler=handler2)
    msgbus.subscribe(topic = "OKX.order", handler=handler3)

    msgbus.publish(topic="BINANCE.order", msg=clock.timestamp_ns())
    msgbus.publish(topic="BYBIT.order", msg=clock.timestamp_ns())
    msgbus.publish(topic="OKX.order", msg=clock.timestamp_ns())
    
    
    msgbus.register(endpoint="pos", handler=handler1)
    msgbus.register(endpoint="pos1", handler=handler2)
    msgbus.register(endpoint="pos2", handler=handler3)
    

    
    msgbus.send(endpoint="pos", msg=clock.timestamp_ns())
    msgbus.send(endpoint="pos1", msg=clock.timestamp_ns())
    msgbus.send(endpoint="pos2", msg=clock.timestamp_ns())
    
    print("done")
    
    

if __name__ == "__main__":
    usage()
