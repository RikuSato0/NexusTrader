import msgspec
from tradebot.types import Order
from tradebot.constants import OrderSide, OrderTimeInForce
from tradebot.exchange.binance.constants import BinanceOrderStatus, BinanceOrderType, BinancePositionSide

class BinanceUserTrade(msgspec.Struct, frozen=True):
    """
    HTTP response from Binance Spot/Margin `GET /api/v3/myTrades` HTTP response from
    Binance USD-M Futures `GET /fapi/v1/userTrades` HTTP response from Binance COIN-M
    Futures `GET /dapi/v1/userTrades`.
    """

    commission: str
    commissionAsset: str
    price: str
    qty: str

    # Parameters not present in 'fills' list (see FULL response of BinanceOrder)
    symbol: str | None = None
    id: int | None = None
    orderId: int | None = None
    time: int | None = None
    quoteQty: str | None = None  # SPOT/MARGIN & USD-M FUTURES only

    # Parameters in SPOT/MARGIN only:
    orderListId: int | None = None  # unless OCO, the value will always be -1
    isBuyer: bool | None = None
    isMaker: bool | None = None
    isBestMatch: bool | None = None
    tradeId: int | None = None  # only in BinanceOrder FULL response

    # Parameters in FUTURES only:
    buyer: bool | None = None
    maker: bool | None = None
    realizedPnl: str | None = None
    side: OrderSide | None = None
    positionSide: str | None = None
    baseQty: str | None = None  # COIN-M FUTURES only
    pair: str | None = None  # COIN-M FUTURES only
    
class BinanceOrder(msgspec.Struct, frozen=True):
    """
    HTTP response from Binance Spot/Margin `GET /api/v3/order` HTTP response from
    Binance USD-M Futures `GET /fapi/v1/order` HTTP response from Binance COIN-M Futures
    `GET /dapi/v1/order`.
    """

    symbol: str
    orderId: int
    clientOrderId: str

    # Parameters not in ACK response:
    price: str | None = None
    origQty: str | None = None
    executedQty: str | None = None
    status: BinanceOrderStatus | None = None
    timeInForce: OrderTimeInForce | None = None
    goodTillDate: int | None = None
    type: BinanceOrderType | None = None
    side: OrderSide | None = None
    stopPrice: str | None = None  # please ignore when order type is TRAILING_STOP_MARKET
    time: int | None = None
    updateTime: int | None = None

    # Parameters in SPOT/MARGIN only:
    orderListId: int | None = None  # Unless OCO, the value will always be -1
    cumulativeQuoteQty: str | None = None  # cumulative quote qty
    icebergQty: str | None = None
    isWorking: bool | None = None
    workingTime: int | None = None
    origQuoteOrderQty: str | None = None
    selfTradePreventionMode: str | None = None
    transactTime: int | None = None  # POST & DELETE methods only
    fills: list[BinanceUserTrade] | None = None  # FULL response only

    # Parameters in FUTURES only:
    avgPrice: str | None = None
    origType: BinanceOrderType | None = None
    reduceOnly: bool | None = None
    positionSide: BinancePositionSide | None = None
    closePosition: bool | None = None
    activatePrice: str | None = None  # activation price, only for TRAILING_STOP_MARKET order
    priceRate: str | None = None  # callback rate, only for TRAILING_STOP_MARKET order
    workingType: str | None = None
    priceProtect: bool | None = None  # if conditional order trigger is protected
    cumQuote: str | None = None  # USD-M FUTURES only
    cumBase: str | None = None  # COIN-M FUTURES only
    pair: str | None = None  # COIN-M FUTURES only
    
    def parse_order(self) -> Order:
        return Order(
            exchange="binance",
            id=self.orderId,
            client_order_id=self.clientOrderId,
            timestamp=self.updateTime,
            symbol=self.symbol,
            
        )
