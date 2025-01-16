from nexustrader.core.entity import EventSystem
from enum import Enum


class OrderStatus(Enum):
    ORDER_FILLED = 0
    ORDER_PLACED = 1
    ORDER_CANCELED = 2


@EventSystem.on(OrderStatus.ORDER_FILLED)
def order_filled(data):
    print(f"Order Filled: {data}")


@EventSystem.on(OrderStatus.ORDER_PLACED)
def order_placed(data):
    print(f"Order Placed: {data}")


@EventSystem.on(OrderStatus.ORDER_CANCELED)
def order_cancelled(data):
    print(f"Order Cancelled: {data}")


def main():
    EventSystem.emit(
        OrderStatus.ORDER_FILLED,
        {
            "order_id": 1,
            "symbol": "BTC/USDT",
            "price": 30000.0,
            "quantity": 1.0,
            "status": "filled",
        },
    )
    EventSystem.emit(
        OrderStatus.ORDER_PLACED,
        {
            "order_id": 2,
            "symbol": "BTC/USDT",
            "price": 30001.0,
            "quantity": 1.0,
            "status": "placed",
        },
    )
    EventSystem.emit(
        OrderStatus.ORDER_CANCELED,
        {
            "order_id": 3,
            "symbol": "BTC/USDT",
            "price": 30002.0,
            "quantity": 1.0,
            "status": "canceled",
        },
    )


if __name__ == "__main__":
    main()
