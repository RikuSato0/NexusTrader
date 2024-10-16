from tradebot.entity import EventSystem
from enum import Enum

class EventType(Enum):
    ORDER_FILLED = "order_filled"
    ORDER_PLACED = "order_placed"
    ORDER_CANCELED = "order_canceled"

@EventSystem.on(EventType.ORDER_FILLED)
def order_filled(data):
    print(f"Order Filled: {data}")


@EventSystem.on(EventType.ORDER_PLACED)
def order_placed(data):
    print(f"Order Placed: {data}")

@EventSystem.on(EventType.ORDER_CANCELED)
def order_cancelled(data):
    print(f"Order Cancelled: {data}")


def main():
    EventSystem.emit(EventType.ORDER_FILLED, {"order_id": 1, "symbol": "BTC/USDT", "price": 30000.0, "quantity": 1.0, "status": "filled"})
    EventSystem.emit(EventType.ORDER_PLACED, {"order_id": 2, "symbol": "BTC/USDT", "price": 30001.0, "quantity": 1.0, "status": "placed"})
    EventSystem.emit(EventType.ORDER_CANCELED, {"order_id": 3, "symbol": "BTC/USDT", "price": 30002.0, "quantity": 1.0, "status": "canceled"})

if __name__ == "__main__":
    main()
