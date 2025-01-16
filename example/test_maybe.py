


from typing import Optional
from returns.maybe import Maybe, maybe
from nexustrader.schema import Order
from nexustrader.constants import OrderStatus, ExchangeType


@maybe  # decorator to convert existing Optional[int] to Maybe[int]
def bad_function(input: int) -> Optional[Order]:
    if input > 3:
        return Order(
            exchange=ExchangeType.BYBIT,
            status=OrderStatus.CANCELED,
            symbol="BTCUSDT.BYBIT",
        )
    else:
        return None

maybe_status: Maybe[bool] = bad_function(10).bind_optional(
    lambda order: order.is_opened,
)

if maybe_status.value_or(False):
    print("Order is opened")
else:
    print("Order is not opened")
# => Maybe will return Some[float] only if there's a non-None value
#    Otherwise, will return Nothing
