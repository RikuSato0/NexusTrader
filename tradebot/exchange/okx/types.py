import msgspec

################################################################################
# Place Order: POST /api/v5/trade/order
################################################################################


class OKXPlaceOrderData(msgspec.Struct):
    ordId: str
    clOrdId: str
    tag: str
    ts: str  # milliseconds when OKX finished order request processing
    sCode: str  # event code, "0" means success
    sMsg: str  # rejection or success message of event execution


class OKXPlaceOrderResponse(msgspec.Struct):
    code: str
    msg: str
    data: list[OKXPlaceOrderData]
    inTime: str  # milliseconds when request hit REST gateway
    outTime: str  # milliseconds when response leaves REST gateway


################################################################################
# Cancel order: POST /api/v5/trade/cancel-order
################################################################################
class OKXCancelOrderData(msgspec.Struct):
    ordId: str
    clOrdId: str
    ts: str  # milliseconds when OKX finished order request processing
    sCode: str  # event code, "0" means success
    sMsg: str  # rejection or success message of event execution


class OKXCancelOrderResponse(msgspec.Struct):
    code: str
    msg: str
    data: list[OKXCancelOrderData]
    inTime: str  # milliseconds when request hit REST gateway
    outTime: str  # milliseconds when response leaves REST gateway
