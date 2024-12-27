import msgspec
from decimal import Decimal
from typing import Final
from typing import Dict, Any, Generic, TypeVar
from tradebot.schema import BaseMarket, Balance
from tradebot.exchange.bybit.constants import (
    BybitProductType,
    BybitOrderSide,
    BybitOrderType,
    BybitTimeInForce,
    BybitOrderStatus,
    BybitTriggerType,
    BybitStopOrderType,
    BybitTriggerDirection,
    BybitPositionIdx,
    BybitPositionSide,
)


BYBIT_PONG: Final[str] = "pong"

class BybitOrder(msgspec.Struct, omit_defaults=True, kw_only=True):
    orderId: str
    orderLinkId: str
    blockTradeId: str | None = None
    symbol: str
    price: str
    qty: str
    side: BybitOrderSide
    isLeverage: str
    positionIdx: int
    orderStatus: BybitOrderStatus
    cancelType: str
    rejectReason: str
    avgPrice: str | None = None
    leavesQty: str
    leavesValue: str
    cumExecQty: str
    cumExecValue: str
    cumExecFee: str
    timeInForce: BybitTimeInForce
    orderType: BybitOrderType
    stopOrderType: BybitStopOrderType
    orderIv: str
    triggerPrice: str
    takeProfit: str
    stopLoss: str
    tpTriggerBy: str
    slTriggerBy: str
    triggerDirection: BybitTriggerDirection = BybitTriggerDirection.NONE
    triggerBy: BybitTriggerType
    lastPriceOnCreated: str
    reduceOnly: bool
    closeOnTrigger: bool
    smpType: str
    smpGroup: int
    smpOrderId: str
    tpslMode: str | None = None
    tpLimitPrice: str
    slLimitPrice: str
    placeType: str
    createdTime: str
    updatedTime: str

class BybitOrderResult(msgspec.Struct):
    orderId: str
    orderLinkId: str


class BybitOrderResponse(msgspec.Struct):
    retCode: int
    retMsg: str
    result: BybitOrderResult
    time: int

class BybitPositionStruct(msgspec.Struct):
    positionIdx: int
    riskId: int
    riskLimitValue: str
    symbol: str
    side: BybitPositionSide
    size: str
    avgPrice: str
    positionValue: str
    tradeMode: int
    positionStatus: str
    autoAddMargin: int
    adlRankIndicator: int
    leverage: str
    positionBalance: str
    markPrice: str
    liqPrice: str
    bustPrice: str
    positionMM: str
    positionIM: str
    takeProfit: str
    stopLoss: str
    trailingStop: str
    unrealisedPnl: str
    cumRealisedPnl: str
    createdTime: str
    updatedTime: str
    tpslMode: str | None = None

T = TypeVar("T")

class BybitListResult(Generic[T], msgspec.Struct):
    list: list[T]
    
class BybitPositionResponse(msgspec.Struct):
    retCode: int
    retMsg: str
    result: BybitListResult[BybitPositionStruct]
    time: int

class BybitOrderHistoryResponse(msgspec.Struct):
    retCode: int
    retMsg: str
    result: BybitListResult[BybitOrder]
    time: int

class BybitOpenOrdersResponse(msgspec.Struct):
    retCode: int
    retMsg: str
    result: BybitListResult[BybitOrder]
    time: int

class BybitResponse(msgspec.Struct, frozen=True):
    retCode: int
    retMsg: str
    result: Dict[str, Any]
    time: int
    retExtInfo: Dict[str, Any] | None = None


class BybitWsMessageGeneral(msgspec.Struct):
    success: bool | None = None
    conn_id: str = ""
    op: str = ""
    topic: str = ""
    ret_msg: str = ""
    args: list[str] = []


class BybitWsOrderbookDepth(msgspec.Struct):
    # symbol
    s: str
    # bids
    b: list[list[str]]
    # asks
    a: list[list[str]]
    # Update ID. Is a sequence. Occasionally, you'll receive "u"=1, which is a
    # snapshot data due to the restart of the service.
    u: int
    # Cross sequence
    seq: int


class BybitWsOrderbookDepthMsg(msgspec.Struct):
    topic: str
    type: str
    ts: int
    data: BybitWsOrderbookDepth


class BybitOrderBook(msgspec.Struct):
    bids: Dict[float, float] = {}
    asks: Dict[float, float] = {}

    def parse_orderbook_depth(self, msg: BybitWsOrderbookDepthMsg, levels: int = 1):
        if msg.type == "snapshot":
            self._handle_snapshot(msg.data)
        elif msg.type == "delta":
            self._handle_delta(msg.data)
        return self._get_orderbook(levels)

    def _handle_snapshot(self, data: BybitWsOrderbookDepth) -> None:
        self.bids.clear()
        self.asks.clear()

        for price, size in data.b:
            self.bids[float(price)] = float(size)

        for price, size in data.a:
            self.asks[float(price)] = float(size)

    def _handle_delta(self, data: BybitWsOrderbookDepth) -> None:
        for price, size in data.b:
            if float(size) == 0:
                self.bids.pop(float(price))
            else:
                self.bids[float(price)] = float(size)

        for price, size in data.a:
            if float(size) == 0:
                self.asks.pop(float(price))
            else:
                self.asks[float(price)] = float(size)

    def _get_orderbook(self, levels: int):
        bids = sorted(self.bids.items(), reverse=True)[:levels]  # bids descending
        asks = sorted(self.asks.items())[:levels]  # asks ascending
        return {
            "bids": bids,
            "asks": asks,
        }
        
class BybitWsTrade(msgspec.Struct):
    # The timestamp (ms) that the order is filled
    T: int
    # Symbol name
    s: str
    # Side of taker. Buy,Sell
    S: str
    # Trade size
    v: str
    # Trade price
    p: str
    # Trade id
    i: str
    # Whether is a block trade or not
    BT: bool
    # Direction of price change
    L: str | None = None
    # Message id unique to options
    id: str | None = None
    # Mark price, unique field for option
    mP: str | None = None
    # Index price, unique field for option
    iP: str | None = None
    # Mark iv, unique field for option
    mIv: str | None = None
    # iv, unique field for option
    iv: str | None = None

class BybitWsTradeMsg(msgspec.Struct):
    topic: str
    type: str
    ts: int
    data: list[BybitWsTrade]

class BybitWsOrder(msgspec.Struct):
    category: BybitProductType
    symbol: str
    orderId: str
    side: BybitOrderSide
    orderType: BybitOrderType
    cancelType: str
    price: str
    qty: str
    orderIv: str
    timeInForce: BybitTimeInForce
    orderStatus: BybitOrderStatus
    orderLinkId: str
    lastPriceOnCreated: str
    reduceOnly: bool
    leavesQty: str
    leavesValue: str
    cumExecQty: str
    cumExecValue: str
    avgPrice: str
    blockTradeId: str
    positionIdx: BybitPositionIdx
    cumExecFee: str
    createdTime: str
    updatedTime: str
    rejectReason: str
    triggerPrice: str
    takeProfit: str
    stopLoss: str
    tpTriggerBy: str
    slTriggerBy: str
    tpLimitPrice: str
    slLimitPrice: str
    closeOnTrigger: bool
    placeType: str
    smpType: str
    smpGroup: int
    smpOrderId: str
    feeCurrency: str
    triggerBy: BybitTriggerType
    stopOrderType: BybitStopOrderType
    triggerDirection: BybitTriggerDirection = BybitTriggerDirection.NONE
    tpslMode: str | None = None
    createType: str | None = None


class BybitWsOrderMsg(msgspec.Struct):
    topic: str
    id: str
    creationTime: int
    data: list[BybitWsOrder]
        


class BybitLotSizeFilter(msgspec.Struct):
    basePrecision: str | None = None
    quotePrecision: str | None = None
    minOrderQty: str | None = None
    maxOrderQty: str | None = None
    minOrderAmt: str | None = None
    maxOrderAmt: str | None = None
    qtyStep: str | None = None
    postOnlyMaxOrderQty: str | None = None
    maxMktOrderQty: str | None = None
    minNotionalValue: str | None = None


class BybitPriceFilter(msgspec.Struct):
    minPrice: str | None = None
    maxPrice: str | None = None
    tickSize: str | None = None


class BybitRiskParameters(msgspec.Struct):
    limitParameter: str | None = None
    marketParameter: str | None = None


class BybitLeverageFilter(msgspec.Struct):
    minLeverage: str | None = None
    maxLeverage: str | None = None
    leverageStep: str | None = None


class BybitMarketInfo(msgspec.Struct):
    """
    {
            "symbol": "BTCUSDT",
            "baseCoin": "BTC",
            "quoteCoin": "USDT",
            "innovation": "0",
            "status": "Trading",
            "marginTrading": "utaOnly",
            "lotSizeFilter": {
                "basePrecision": "0.000001",
                "quotePrecision": "0.00000001",
                "minOrderQty": "0.000048",
                "maxOrderQty": "71.73956243",
                "minOrderAmt": "1",
                "maxOrderAmt": "4000000"
            },
            "priceFilter": {
                "tickSize": "0.01"
            },
            "riskParameters": {
                "limitParameter": "0.02",
                "marketParameter": "0.02"
            }
    },

    {
            "symbol": "BTC-26SEP25-300000-C",
            "status": "Trading",
            "baseCoin": "BTC",
            "quoteCoin": "USDC",
            "settleCoin": "USDC",
            "optionsType": "Call",
            "launchTime": "1727942400000",
            "deliveryTime": "1758873600000",
            "deliveryFeeRate": "0.00015",
            "priceFilter": {
                "minPrice": "5",
                "maxPrice": "10000000",
                "tickSize": "5"
            },
            "lotSizeFilter": {
                "maxOrderQty": "500",
                "minOrderQty": "0.01",
                "qtyStep": "0.01"
            }
    }

    {
            "symbol": "10000000AIDOGEUSDT",
            "contractType": "LinearPerpetual",
            "status": "Trading",
            "baseCoin": "10000000AIDOGE",
            "quoteCoin": "USDT",
            "launchTime": "1709542899000",
            "deliveryTime": "0",
            "deliveryFeeRate": "",
            "priceScale": "6",
            "leverageFilter": {
                "minLeverage": "1",
                "maxLeverage": "12.50",
                "leverageStep": "0.01"
            },
            "priceFilter": {
                "minPrice": "0.000001",
                "maxPrice": "1.999998",
                "tickSize": "0.000001"
            },
            "lotSizeFilter": {
                "maxOrderQty": "15000000",
                "minOrderQty": "100",
                "qtyStep": "100",
                "postOnlyMaxOrderQty": "15000000",
                "maxMktOrderQty": "3000000",
                "minNotionalValue": "5"
            },
            "unifiedMarginTrade": true,
            "fundingInterval": "480",
            "settleCoin": "USDT",
            "copyTrading": "none",
            "upperFundingRate": "0.03",
            "lowerFundingRate": "-0.03",
            "isPreListing": false,
            "preListingInfo": null
        }
    """

    symbol: str = None
    baseCoin: str = None
    quoteCoin: str = None
    innovation: str = None
    status: str = None
    marginTrading: str = None
    lotSizeFilter: BybitLotSizeFilter = None
    priceFilter: BybitPriceFilter = None
    riskParameters: BybitRiskParameters = None
    settleCoin: str | None = None
    optionsType: str | None = None
    launchTime: str | None = None
    deliveryTime: str | None = None
    deliveryFeeRate: str | None = None
    contractType: str | None = None
    priceScale: str | None = None
    leverageFilter: BybitLeverageFilter = None
    unifiedMarginTrade: bool | None = None
    fundingInterval: str | int | None = None
    copyTrading: str | None = None
    upperFundingRate: str | None = None
    lowerFundingRate: str | None = None
    isPreListing: bool | None = None
    preListingInfo: dict | None = None


class BybitMarket(BaseMarket):
    """
    "BTC/USDT": {
        "id": "BTCUSDT",
        "lowercaseId": null,
        "symbol": "BTC/USDT",
        "base": "BTC",
        "quote": "USDT",
        "settle": null,
        "baseId": "BTC",
        "quoteId": "USDT",
        "settleId": null,
        "type": "spot",
        "spot": true,
        "margin": true,
        "swap": false,
        "future": false,
        "option": false,
        "index": false,
        "active": true,
        "contract": false,
        "linear": null,
        "inverse": null,
        "subType": null,
        "taker": 0.001,
        "maker": 0.001,
        "contractSize": null,
        "expiry": null,
        "expiryDatetime": null,
        "strike": null,
        "optionType": null,
        "precision": {
            "amount": 1e-06,
            "price": 0.01,
            "cost": null,
            "base": null,
            "quote": null
        },
        "limits": {
            "leverage": {
                "min": 1.0,
                "max": null
            },
            "amount": {
                "min": 4.8e-05,
                "max": 71.73956243
            },
            "price": {
                "min": null,
                "max": null
            },
            "cost": {
                "min": 1.0,
                "max": 4000000.0
            }
        },
        "marginModes": {
            "cross": null,
            "isolated": null
        },
        "created": null,
        "info": {
            "symbol": "BTCUSDT",
            "baseCoin": "BTC",
            "quoteCoin": "USDT",
            "innovation": "0",
            "status": "Trading",
            "marginTrading": "utaOnly",
            "lotSizeFilter": {
                "basePrecision": "0.000001",
                "quotePrecision": "0.00000001",
                "minOrderQty": "0.000048",
                "maxOrderQty": "71.73956243",
                "minOrderAmt": "1",
                "maxOrderAmt": "4000000"
            },
            "priceFilter": {
                "tickSize": "0.01"
            },
            "riskParameters": {
                "limitParameter": "0.02",
                "marketParameter": "0.02"
            }
        },
        "tierBased": true,
        "percentage": true,
        "feeSide": "get"
    },
    """

    info: BybitMarketInfo
    feeSide: str

class BybitCoinBalance(msgspec.Struct):
    availableToBorrow: str
    bonus: str
    accruedInterest: str
    availableToWithdraw: str
    totalOrderIM: str
    equity: str
    usdValue: str
    borrowAmount: str
    # Sum of maintenance margin for all positions.
    totalPositionMM: str
    # Sum of initial margin of all positions + Pre-occupied liquidation fee.
    totalPositionIM: str
    walletBalance: str
    # Unrealised P&L
    unrealisedPnl: str
    # Cumulative Realised P&L
    cumRealisedPnl: str
    locked: str
    # Whether it can be used as a margin collateral currency (platform)
    collateralSwitch: bool
    # Whether the collateral is turned on by the user
    marginCollateral: bool
    coin: str

    def parse_to_balance(self) -> Balance:
        locked = Decimal(self.locked)
        free = Decimal(self.walletBalance) - locked
        return Balance(
            asset=self.coin,
            locked=locked,
            free=free,
        )


class BybitWalletBalance(msgspec.Struct):
    totalEquity: str
    accountIMRate: str
    totalMarginBalance: str
    totalInitialMargin: str
    accountType: str
    totalAvailableBalance: str
    accountMMRate: str
    totalPerpUPL: str
    totalWalletBalance: str
    accountLTV: str
    totalMaintenanceMargin: str
    coin: list[BybitCoinBalance]

    def parse_to_balance(self) -> list[Balance]:
        return [coin.parse_to_balance() for coin in self.coin]


class BybitWalletBalanceResponse(msgspec.Struct):
    retCode: int
    retMsg: str
    result: BybitListResult[BybitWalletBalance]
    time: int
