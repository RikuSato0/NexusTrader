import msgspec
from decimal import Decimal
from typing import Any, Dict, List
from tradebot.schema import BaseMarket, Balance
from tradebot.constants import OrderSide, TimeInForce
from tradebot.exchange.binance.constants import (
    BinanceOrderStatus,
    BinanceOrderType,
    BinancePositionSide,
    BinanceWsEventType,
    BinanceKlineInterval,
    BinanceUserDataStreamWsEventType,
    BinanceOrderSide,
    BinanceTimeInForce,
    BinanceExecutionType,
    BinanceFuturesWorkingType,
    BinanceBusinessUnit,
)


class BinanceFuturesBalanceInfo(msgspec.Struct, frozen=True):
    """
    HTTP response 'inner struct' from Binance Futures GET /fapi/v2/account (HMAC
    SHA256).
    """

    asset: str  # asset name
    walletBalance: str  # wallet balance
    unrealizedProfit: str  # unrealized profit
    marginBalance: str  # margin balance
    maintMargin: str  # maintenance margin required
    initialMargin: str  # total initial margin required with current mark price
    positionInitialMargin: str  # initial margin required for positions with current mark price
    openOrderInitialMargin: str  # initial margin required for open orders with current mark price
    crossWalletBalance: str  # crossed wallet balance
    crossUnPnl: str  # unrealized profit of crossed positions
    availableBalance: str  # available balance
    maxWithdrawAmount: str  # maximum amount for transfer out
    # whether the asset can be used as margin in Multi - Assets mode
    marginAvailable: bool | None = None
    updateTime: int | None = None  # last update time
    
    def parse_to_balance(self) -> Balance:
        free = Decimal(self.availableBalance)
        locked = Decimal(self.marginBalance) - free
        return Balance(
            asset=self.asset,
            free=free,
            locked=locked,
        )

class BinanceFuturesAccountInfo(msgspec.Struct, kw_only=True):
    """
    HTTP response from Binance Futures GET /fapi/v2/account (HMAC SHA256).
    """

    feeTier: int  # account commission tier
    canTrade: bool  # if can trade
    canDeposit: bool  # if can transfer in asset
    canWithdraw: bool  # if can transfer out asset
    updateTime: int
    totalInitialMargin: str | None = (
        None  # total initial margin required with current mark price (useless with isolated positions), only for USDT
    )
    totalMaintMargin: str | None = None  # total maintenance margin required, only for USDT asset
    totalWalletBalance: str | None = None  # total wallet balance, only for USDT asset
    totalUnrealizedProfit: str | None = None  # total unrealized profit, only for USDT asset
    totalMarginBalance: str | None = None  # total margin balance, only for USDT asset
    # initial margin required for positions with current mark price, only for USDT asset
    totalPositionInitialMargin: str | None = None
    # initial margin required for open orders with current mark price, only for USDT asset
    totalOpenOrderInitialMargin: str | None = None
    totalCrossWalletBalance: str | None = None  # crossed wallet balance, only for USDT asset
    # unrealized profit of crossed positions, only for USDT asset
    totalCrossUnPnl: str | None = None
    availableBalance: str | None = None  # available balance, only for USDT asset
    maxWithdrawAmount: str | None = None  # maximum amount for transfer out, only for USDT asset
    assets: list[BinanceFuturesBalanceInfo]

    def parse_to_balances(self) -> List[Balance]:
        return [balance.parse_to_balance() for balance in self.assets]

class BinanceSpotBalanceInfo(msgspec.Struct):
    """
    HTTP response 'inner struct' from Binance Spot/Margin GET /api/v3/account (HMAC
    SHA256).
    """

    asset: str
    free: str
    locked: str

    def parse_to_balance(self) -> Balance:
        return Balance(
            asset=self.asset,
            free=Decimal(self.free),
            locked=Decimal(self.locked),
        )

class BinanceSpotAccountInfo(msgspec.Struct, frozen=True):
    """
    HTTP response from Binance Spot/Margin GET /api/v3/account (HMAC SHA256).
    """

    makerCommission: int
    takerCommission: int
    buyerCommission: int
    sellerCommission: int
    canTrade: bool
    canWithdraw: bool
    canDeposit: bool
    updateTime: int
    accountType: str
    balances: list[BinanceSpotBalanceInfo]
    permissions: list[str]

    def parse_to_balances(self) -> List[Balance]:
        return [balance.parse_to_balance() for balance in self.balances]

class BinanceSpotOrderUpdateMsg(msgspec.Struct, kw_only=True):
    """
    WebSocket message 'inner struct' for Binance Spot/Margin Order Update events.
    """

    e: BinanceUserDataStreamWsEventType
    E: int  # Event time
    s: str  # Symbol
    c: str  # Client order ID
    S: BinanceOrderSide 
    o: BinanceOrderType
    f: BinanceTimeInForce
    q: str  # Original Quantity
    p: str  # Original Price
    P: str  # Stop price
    F: str  # Iceberg quantity
    g: int  # Order list ID
    C: str  # Original client order ID; This is the ID of the order being canceled
    x: BinanceExecutionType
    X: BinanceOrderStatus
    r: str  # Order reject reason; will be an error code
    i: int  # Order ID
    l: str  # Order Last Filled Quantity # noqa
    z: str  # Order Filled Accumulated Quantity
    L: str  # Last Filled Price
    n: str | None = None  # Commission, will not push if no commission
    N: str | None = None  # Commission Asset, will not push if no commission
    T: int  # Order Trade Time
    t: int  # Trade ID
    I: int  # Ignore # noqa
    w: bool  # Is the order on the book?
    m: bool  # Is trade the maker side
    M: bool  # Ignore 
    O: int  # Order creation time # noqa
    Z: str  # Cumulative quote asset transacted quantity
    Y: str  # Last quote asset transacted quantity (i.e. lastPrice * lastQty)
    Q: str  # Quote Order Qty

class BinanceFuturesOrderData(msgspec.Struct, kw_only=True):
    """
    WebSocket message 'inner struct' for Binance Futures Order Update events.

    Client Order ID 'c':
     - starts with "autoclose-": liquidation order/
     - starts with "adl_autoclose": ADL auto close order/

    """
    s: str  # Symbol
    c: str  # Client Order ID
    S: BinanceOrderSide
    o: BinanceOrderType
    f: BinanceTimeInForce
    q: str  # Original Quantity
    p: str  # Original Price
    ap: str  # Average Price
    sp: str | None = None  # Stop Price. Ignore with TRAILING_STOP_MARKET order
    x: BinanceExecutionType
    X: BinanceOrderStatus
    i: int  # Order ID
    l: str  # Order Last Filled Quantity # noqa
    z: str  # Order Filled Accumulated Quantity
    L: str  # Last Filled Price
    N: str | None = None  # Commission Asset, will not push if no commission
    n: str | None = None  # Commission, will not push if no commission
    T: int  # Order Trade Time
    t: int  # Trade ID
    b: str  # Bids Notional
    a: str  # Ask Notional
    m: bool  # Is trade the maker side
    R: bool  # Is reduce only
    wt: BinanceFuturesWorkingType
    ot: BinanceOrderType
    ps: BinancePositionSide
    cp: bool | None = None  # If Close-All, pushed with conditional order
    AP: str | None = (
        None  # Activation Price, only pushed with TRAILING_STOP_MARKET order
    )
    cr: str | None = None  # Callback Rate, only pushed with TRAILING_STOP_MARKET order
    pP: bool  # ignore
    si: int  # ignore
    ss: int  # ignore
    rp: str  # Realized Profit of the trade
    gtd: int  # TIF GTD order auto cancel time


class BinanceFuturesOrderUpdateMsg(msgspec.Struct, kw_only = True):
    """
    WebSocket message for Binance Futures Order Update events.
    """
    e: BinanceUserDataStreamWsEventType
    E: int  # Event Time
    T: int  # Transaction Time
    fs: BinanceBusinessUnit | None = None  # Event business unit. 'UM' for USDS-M futures and 'CM' for COIN-M futures 
    o: BinanceFuturesOrderData


class BinanceMarkPrice(msgspec.Struct):
    """
     {
        "e": "markPriceUpdate",     // Event type
        "E": 1562305380000,         // Event time
        "s": "BTCUSDT",             // Symbol
        "p": "11794.15000000",      // Mark price
        "i": "11784.62659091",      // Index price
        "P": "11784.25641265",      // Estimated Settle Price, only useful in the last hour before the settlement starts
        "r": "0.00038167",          // Funding rate
        "T": 1562306400000          // Next funding time
    }
    """
    e: BinanceWsEventType
    E: int
    s: str
    p: str
    i: str
    P: str
    r: str
    T: int


class BinanceKlineData(msgspec.Struct):
    e: BinanceWsEventType
    t: int  # Kline start time
    T: int  # Kline close time
    s: str  # Symbol
    i: BinanceKlineInterval  # Interval
    f: int  # First trade ID
    L: int  # Last trade ID
    o: str  # Open price
    c: str  # Close price
    h: str  # High price
    l: str  # Low price # noqa
    v: str  # Base asset volume
    n: int  # Number of trades
    x: bool  # Is this kline closed?
    q: str  # Quote asset volume
    V: str  # Taker buy base asset volume
    Q: str  # Taker buy quote asset volume
    B: str  # Ignore


class BinanceKline(msgspec.Struct):
    e: BinanceWsEventType
    E: int
    s: str
    k: BinanceKlineData


class BinanceTradeData(msgspec.Struct):
    e: BinanceWsEventType
    E: int
    s: str
    t: int
    p: str
    q: str
    T: int


class BinanceSpotBookTicker(msgspec.Struct):
    """
      {
        "u":400900217,     // order book updateId
        "s":"BNBUSDT",     // symbol
        "b":"25.35190000", // best bid price
        "B":"31.21000000", // best bid qty
        "a":"25.36520000", // best ask price
        "A":"40.66000000"  // best ask qty
    }
    """
    u: int
    s: str
    b: str
    B: str
    a: str
    A: str


class BinanceFuturesBookTicker(msgspec.Struct):
    """
      {
      "e":"bookTicker",         // event type
      "u":400900217,            // order book updateId
      "E": 1568014460893,       // event time
      "T": 1568014460891,       // transaction time
      "s":"BNBUSDT",            // symbol
      "b":"25.35190000",        // best bid price
      "B":"31.21000000",        // best bid qty
      "a":"25.36520000",        // best ask price
      "A":"40.66000000"         // best ask qty
    }
    """
    e: BinanceWsEventType
    u: int
    E: int
    T: int
    s: str
    b: str
    B: str
    a: str
    A: str


class BinanceWsMessageGeneral(msgspec.Struct):
    e: BinanceWsEventType | None = None
    u: int | None = None


class BinanceUserDataStreamMsg(msgspec.Struct):
    e: BinanceUserDataStreamWsEventType | None = None


class BinanceListenKey(msgspec.Struct):
    listenKey: str


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
    timeInForce: TimeInForce | None = None
    goodTillDate: int | None = None
    type: BinanceOrderType | None = None
    side: OrderSide | None = None
    stopPrice: str | None = (
        None  # please ignore when order type is TRAILING_STOP_MARKET
    )
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
    activatePrice: str | None = (
        None  # activation price, only for TRAILING_STOP_MARKET order
    )
    priceRate: str | None = None  # callback rate, only for TRAILING_STOP_MARKET order
    workingType: str | None = None
    priceProtect: bool | None = None  # if conditional order trigger is protected
    cumQuote: str | None = None  # USD-M FUTURES only
    cumBase: str | None = None  # COIN-M FUTURES only
    pair: str | None = None  # COIN-M FUTURES only


class BinanceMarketInfo(msgspec.Struct):
    """
    {
      "symbol": "ETHBTC",
      "status": "TRADING",
      "baseAsset": "ETH",
      "baseAssetPrecision": "8",
      "quoteAsset": "BTC",
      "quotePrecision": "8",
      "quoteAssetPrecision": "8",
      "baseCommissionPrecision": "8",
      "quoteCommissionPrecision": "8",
      "orderTypes": [
        "LIMIT",
        "LIMIT_MAKER",
        "MARKET",
        "STOP_LOSS",
        "STOP_LOSS_LIMIT",
        "TAKE_PROFIT",
        "TAKE_PROFIT_LIMIT"
      ],
      "icebergAllowed": true,
      "ocoAllowed": true,
      "otoAllowed": true,
      "quoteOrderQtyMarketAllowed": true,
      "allowTrailingStop": true,
      "cancelReplaceAllowed": true,
      "isSpotTradingAllowed": true,
      "isMarginTradingAllowed": true,
      "filters": [
        {
          "filterType": "PRICE_FILTER",
          "minPrice": "0.00001000",
          "maxPrice": "922327.00000000",
          "tickSize": "0.00001000"
        },
        {
          "filterType": "LOT_SIZE",
          "minQty": "0.00010000",
          "maxQty": "100000.00000000",
          "stepSize": "0.00010000"
        },
        {
          "filterType": "ICEBERG_PARTS",
          "limit": "10"
        },
        {
          "filterType": "MARKET_LOT_SIZE",
          "minQty": "0.00000000",
          "maxQty": "2716.24643375",
          "stepSize": "0.00000000"
        },
        {
          "filterType": "TRAILING_DELTA",
          "minTrailingAboveDelta": "10",
          "maxTrailingAboveDelta": "2000",
          "minTrailingBelowDelta": "10",
          "maxTrailingBelowDelta": "2000"
        },
        {
          "filterType": "PERCENT_PRICE_BY_SIDE",
          "bidMultiplierUp": "5",
          "bidMultiplierDown": "0.2",
          "askMultiplierUp": "5",
          "askMultiplierDown": "0.2",
          "avgPriceMins": "5"
        },
        {
          "filterType": "NOTIONAL",
          "minNotional": "0.00010000",
          "applyMinToMarket": true,
          "maxNotional": "9000000.00000000",
          "applyMaxToMarket": false,
          "avgPriceMins": "5"
        },
        {
          "filterType": "MAX_NUM_ORDERS",
          "maxNumOrders": "200"
        },
        {
          "filterType": "MAX_NUM_ALGO_ORDERS",
          "maxNumAlgoOrders": "5"
        }
      ],
      "permissions": [],
      "permissionSets": [
        [
          "SPOT",
          "MARGIN",
          "TRD_GRP_004",
          "TRD_GRP_005",
          "TRD_GRP_006",
          "TRD_GRP_008",
          "TRD_GRP_009",
          "TRD_GRP_010",
          "TRD_GRP_011",
          "TRD_GRP_012",
          "TRD_GRP_013",
          "TRD_GRP_014",
          "TRD_GRP_015",
          "TRD_GRP_016",
          "TRD_GRP_017",
          "TRD_GRP_018",
          "TRD_GRP_019",
          "TRD_GRP_020",
          "TRD_GRP_021",
          "TRD_GRP_022",
          "TRD_GRP_023",
          "TRD_GRP_024",
          "TRD_GRP_025",
          "TRD_GRP_026",
          "TRD_GRP_027",
          "TRD_GRP_028",
          "TRD_GRP_029",
          "TRD_GRP_030",
          "TRD_GRP_031",
          "TRD_GRP_032",
          "TRD_GRP_033",
          "TRD_GRP_034",
          "TRD_GRP_035",
          "TRD_GRP_036",
          "TRD_GRP_037",
          "TRD_GRP_038",
          "TRD_GRP_039",
          "TRD_GRP_040",
          "TRD_GRP_041",
          "TRD_GRP_042",
          "TRD_GRP_043",
          "TRD_GRP_044",
          "TRD_GRP_045",
          "TRD_GRP_046",
          "TRD_GRP_047",
          "TRD_GRP_048",
          "TRD_GRP_049",
          "TRD_GRP_050",
          "TRD_GRP_051",
          "TRD_GRP_052",
          "TRD_GRP_053",
          "TRD_GRP_054",
          "TRD_GRP_055",
          "TRD_GRP_056",
          "TRD_GRP_057",
          "TRD_GRP_058",
          "TRD_GRP_059",
          "TRD_GRP_060",
          "TRD_GRP_061",
          "TRD_GRP_062",
          "TRD_GRP_063",
          "TRD_GRP_064",
          "TRD_GRP_065",
          "TRD_GRP_066",
          "TRD_GRP_067",
          "TRD_GRP_068",
          "TRD_GRP_069",
          "TRD_GRP_070",
          "TRD_GRP_071",
          "TRD_GRP_072",
          "TRD_GRP_073",
          "TRD_GRP_074",
          "TRD_GRP_075",
          "TRD_GRP_076",
          "TRD_GRP_077",
          "TRD_GRP_078",
          "TRD_GRP_079",
          "TRD_GRP_080",
          "TRD_GRP_081",
          "TRD_GRP_082",
          "TRD_GRP_083",
          "TRD_GRP_084",
          "TRD_GRP_085",
          "TRD_GRP_086",
          "TRD_GRP_087",
          "TRD_GRP_088",
          "TRD_GRP_089",
          "TRD_GRP_090",
          "TRD_GRP_091",
          "TRD_GRP_092",
          "TRD_GRP_093",
          "TRD_GRP_094",
          "TRD_GRP_095",
          "TRD_GRP_096",
          "TRD_GRP_097",
          "TRD_GRP_098",
          "TRD_GRP_099",
          "TRD_GRP_100",
          "TRD_GRP_101",
          "TRD_GRP_102",
          "TRD_GRP_103",
          "TRD_GRP_104",
          "TRD_GRP_105",
          "TRD_GRP_106",
          "TRD_GRP_107",
          "TRD_GRP_108",
          "TRD_GRP_109",
          "TRD_GRP_110",
          "TRD_GRP_111",
          "TRD_GRP_112",
          "TRD_GRP_113",
          "TRD_GRP_114",
          "TRD_GRP_115",
          "TRD_GRP_116",
          "TRD_GRP_117",
          "TRD_GRP_118",
          "TRD_GRP_119",
          "TRD_GRP_120",
          "TRD_GRP_121",
          "TRD_GRP_122",
          "TRD_GRP_123",
          "TRD_GRP_124",
          "TRD_GRP_125",
          "TRD_GRP_126",
          "TRD_GRP_127",
          "TRD_GRP_128",
          "TRD_GRP_129",
          "TRD_GRP_130",
          "TRD_GRP_131",
          "TRD_GRP_132",
          "TRD_GRP_133",
          "TRD_GRP_134",
          "TRD_GRP_135",
          "TRD_GRP_136",
          "TRD_GRP_137",
          "TRD_GRP_138",
          "TRD_GRP_139",
          "TRD_GRP_140",
          "TRD_GRP_141",
          "TRD_GRP_142",
          "TRD_GRP_143",
          "TRD_GRP_144",
          "TRD_GRP_145",
          "TRD_GRP_146",
          "TRD_GRP_147",
          "TRD_GRP_148",
          "TRD_GRP_149",
          "TRD_GRP_150",
          "TRD_GRP_151",
          "TRD_GRP_152",
          "TRD_GRP_153",
          "TRD_GRP_154",
          "TRD_GRP_155",
          "TRD_GRP_156",
          "TRD_GRP_157",
          "TRD_GRP_158",
          "TRD_GRP_159",
          "TRD_GRP_160",
          "TRD_GRP_161",
          "TRD_GRP_162",
          "TRD_GRP_163",
          "TRD_GRP_164",
          "TRD_GRP_165",
          "TRD_GRP_166",
          "TRD_GRP_167",
          "TRD_GRP_168",
          "TRD_GRP_169",
          "TRD_GRP_170",
          "TRD_GRP_171",
          "TRD_GRP_172",
          "TRD_GRP_173",
          "TRD_GRP_174",
          "TRD_GRP_175",
          "TRD_GRP_176",
          "TRD_GRP_177",
          "TRD_GRP_178",
          "TRD_GRP_179",
          "TRD_GRP_180",
          "TRD_GRP_181",
          "TRD_GRP_182",
          "TRD_GRP_183",
          "TRD_GRP_184"
        ]
      ],
      "defaultSelfTradePreventionMode": "EXPIRE_MAKER",
      "allowedSelfTradePreventionModes": [
        "EXPIRE_TAKER",
        "EXPIRE_MAKER",
        "EXPIRE_BOTH"
      ]
    }
    """

    symbol: str = None
    status: str = None
    baseAsset: str = None
    baseAssetPrecision: str | int = None
    quoteAsset: str = None
    quotePrecision: str | int = None
    quoteAssetPrecision: str | int = None
    baseCommissionPrecision: str | int = None
    quoteCommissionPrecision: str | int = None
    orderTypes: List[BinanceOrderType] = None
    icebergAllowed: bool = None
    ocoAllowed: bool = None
    otoAllowed: bool = None
    quoteOrderQtyMarketAllowed: bool = None
    allowTrailingStop: bool = None
    cancelReplaceAllowed: bool = None
    isSpotTradingAllowed: bool = None
    isMarginTradingAllowed: bool = None
    filters: List[Dict[str, Any]] = None
    permissions: List[str] = None
    permissionSets: List[List[str]] = None
    defaultSelfTradePreventionMode: str = None
    allowedSelfTradePreventionModes: List[str] = None


class BinanceMarket(BaseMarket):
    """
       {
      "id": "ETHBTC",
      "lowercaseId": "ethbtc",
      "symbol": "ETH/BTC",
      "base": "ETH",
      "quote": "BTC",
      "settle": null,
      "baseId": "ETH",
      "quoteId": "BTC",
      "settleId": null,
      "type": "spot",
      "spot": true,
      "margin": true,
      "swap": false,
      "future": false,
      "option": false,
      "index": null,
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
        "amount": 0.0001,
        "price": 1e-05,
        "cost": null,
        "base": 1e-08,
        "quote": 1e-08
      },
      "limits": {
        "leverage": {
          "min": null,
          "max": null
        },
        "amount": {
          "min": 0.0001,
          "max": 100000.0
        },
        "price": {
          "min": 1e-05,
          "max": 922327.0
        },
        "cost": {
          "min": 0.0001,
          "max": 9000000.0
        },
        "market": {
          "min": 0.0,
          "max": 2716.24643375
        }
      },
      "marginModes": {
        "cross": false,
        "isolated": false
      },
      "created": null,
      "info": {
        "symbol": "ETHBTC",
        "status": "TRADING",
        "baseAsset": "ETH",
        "baseAssetPrecision": "8",
        "quoteAsset": "BTC",
        "quotePrecision": "8",
        "quoteAssetPrecision": "8",
        "baseCommissionPrecision": "8",
        "quoteCommissionPrecision": "8",
        "orderTypes": [
          "LIMIT",
          "LIMIT_MAKER",
          "MARKET",
          "STOP_LOSS",
          "STOP_LOSS_LIMIT",
          "TAKE_PROFIT",
          "TAKE_PROFIT_LIMIT"
        ],
        "icebergAllowed": true,
        "ocoAllowed": true,
        "otoAllowed": true,
        "quoteOrderQtyMarketAllowed": true,
        "allowTrailingStop": true,
        "cancelReplaceAllowed": true,
        "isSpotTradingAllowed": true,
        "isMarginTradingAllowed": true,
        "filters": [
          {
            "filterType": "PRICE_FILTER",
            "minPrice": "0.00001000",
            "maxPrice": "922327.00000000",
            "tickSize": "0.00001000"
          },
          {
            "filterType": "LOT_SIZE",
            "minQty": "0.00010000",
            "maxQty": "100000.00000000",
            "stepSize": "0.00010000"
          },
          {
            "filterType": "ICEBERG_PARTS",
            "limit": "10"
          },
          {
            "filterType": "MARKET_LOT_SIZE",
            "minQty": "0.00000000",
            "maxQty": "2716.24643375",
            "stepSize": "0.00000000"
          },
          {
            "filterType": "TRAILING_DELTA",
            "minTrailingAboveDelta": "10",
            "maxTrailingAboveDelta": "2000",
            "minTrailingBelowDelta": "10",
            "maxTrailingBelowDelta": "2000"
          },
          {
            "filterType": "PERCENT_PRICE_BY_SIDE",
            "bidMultiplierUp": "5",
            "bidMultiplierDown": "0.2",
            "askMultiplierUp": "5",
            "askMultiplierDown": "0.2",
            "avgPriceMins": "5"
          },
          {
            "filterType": "NOTIONAL",
            "minNotional": "0.00010000",
            "applyMinToMarket": true,
            "maxNotional": "9000000.00000000",
            "applyMaxToMarket": false,
            "avgPriceMins": "5"
          },
          {
            "filterType": "MAX_NUM_ORDERS",
            "maxNumOrders": "200"
          },
          {
            "filterType": "MAX_NUM_ALGO_ORDERS",
            "maxNumAlgoOrders": "5"
          }
        ],
        "permissions": [],
        "permissionSets": [
          [
            "SPOT",
            "MARGIN",
            "TRD_GRP_004",
            "TRD_GRP_005",
            "TRD_GRP_006",
            "TRD_GRP_008",
            "TRD_GRP_009",
            "TRD_GRP_010",
            "TRD_GRP_011",
            "TRD_GRP_012",
            "TRD_GRP_013",
            "TRD_GRP_014",
            "TRD_GRP_015",
            "TRD_GRP_016",
            "TRD_GRP_017",
            "TRD_GRP_018",
            "TRD_GRP_019",
            "TRD_GRP_020",
            "TRD_GRP_021",
            "TRD_GRP_022",
            "TRD_GRP_023",
            "TRD_GRP_024",
            "TRD_GRP_025",
            "TRD_GRP_026",
            "TRD_GRP_027",
            "TRD_GRP_028",
            "TRD_GRP_029",
            "TRD_GRP_030",
            "TRD_GRP_031",
            "TRD_GRP_032",
            "TRD_GRP_033",
            "TRD_GRP_034",
            "TRD_GRP_035",
            "TRD_GRP_036",
            "TRD_GRP_037",
            "TRD_GRP_038",
            "TRD_GRP_039",
            "TRD_GRP_040",
            "TRD_GRP_041",
            "TRD_GRP_042",
            "TRD_GRP_043",
            "TRD_GRP_044",
            "TRD_GRP_045",
            "TRD_GRP_046",
            "TRD_GRP_047",
            "TRD_GRP_048",
            "TRD_GRP_049",
            "TRD_GRP_050",
            "TRD_GRP_051",
            "TRD_GRP_052",
            "TRD_GRP_053",
            "TRD_GRP_054",
            "TRD_GRP_055",
            "TRD_GRP_056",
            "TRD_GRP_057",
            "TRD_GRP_058",
            "TRD_GRP_059",
            "TRD_GRP_060",
            "TRD_GRP_061",
            "TRD_GRP_062",
            "TRD_GRP_063",
            "TRD_GRP_064",
            "TRD_GRP_065",
            "TRD_GRP_066",
            "TRD_GRP_067",
            "TRD_GRP_068",
            "TRD_GRP_069",
            "TRD_GRP_070",
            "TRD_GRP_071",
            "TRD_GRP_072",
            "TRD_GRP_073",
            "TRD_GRP_074",
            "TRD_GRP_075",
            "TRD_GRP_076",
            "TRD_GRP_077",
            "TRD_GRP_078",
            "TRD_GRP_079",
            "TRD_GRP_080",
            "TRD_GRP_081",
            "TRD_GRP_082",
            "TRD_GRP_083",
            "TRD_GRP_084",
            "TRD_GRP_085",
            "TRD_GRP_086",
            "TRD_GRP_087",
            "TRD_GRP_088",
            "TRD_GRP_089",
            "TRD_GRP_090",
            "TRD_GRP_091",
            "TRD_GRP_092",
            "TRD_GRP_093",
            "TRD_GRP_094",
            "TRD_GRP_095",
            "TRD_GRP_096",
            "TRD_GRP_097",
            "TRD_GRP_098",
            "TRD_GRP_099",
            "TRD_GRP_100",
            "TRD_GRP_101",
            "TRD_GRP_102",
            "TRD_GRP_103",
            "TRD_GRP_104",
            "TRD_GRP_105",
            "TRD_GRP_106",
            "TRD_GRP_107",
            "TRD_GRP_108",
            "TRD_GRP_109",
            "TRD_GRP_110",
            "TRD_GRP_111",
            "TRD_GRP_112",
            "TRD_GRP_113",
            "TRD_GRP_114",
            "TRD_GRP_115",
            "TRD_GRP_116",
            "TRD_GRP_117",
            "TRD_GRP_118",
            "TRD_GRP_119",
            "TRD_GRP_120",
            "TRD_GRP_121",
            "TRD_GRP_122",
            "TRD_GRP_123",
            "TRD_GRP_124",
            "TRD_GRP_125",
            "TRD_GRP_126",
            "TRD_GRP_127",
            "TRD_GRP_128",
            "TRD_GRP_129",
            "TRD_GRP_130",
            "TRD_GRP_131",
            "TRD_GRP_132",
            "TRD_GRP_133",
            "TRD_GRP_134",
            "TRD_GRP_135",
            "TRD_GRP_136",
            "TRD_GRP_137",
            "TRD_GRP_138",
            "TRD_GRP_139",
            "TRD_GRP_140",
            "TRD_GRP_141",
            "TRD_GRP_142",
            "TRD_GRP_143",
            "TRD_GRP_144",
            "TRD_GRP_145",
            "TRD_GRP_146",
            "TRD_GRP_147",
            "TRD_GRP_148",
            "TRD_GRP_149",
            "TRD_GRP_150",
            "TRD_GRP_151",
            "TRD_GRP_152",
            "TRD_GRP_153",
            "TRD_GRP_154",
            "TRD_GRP_155",
            "TRD_GRP_156",
            "TRD_GRP_157",
            "TRD_GRP_158",
            "TRD_GRP_159",
            "TRD_GRP_160",
            "TRD_GRP_161",
            "TRD_GRP_162",
            "TRD_GRP_163",
            "TRD_GRP_164",
            "TRD_GRP_165",
            "TRD_GRP_166",
            "TRD_GRP_167",
            "TRD_GRP_168",
            "TRD_GRP_169",
            "TRD_GRP_170",
            "TRD_GRP_171",
            "TRD_GRP_172",
            "TRD_GRP_173",
            "TRD_GRP_174",
            "TRD_GRP_175",
            "TRD_GRP_176",
            "TRD_GRP_177",
            "TRD_GRP_178",
            "TRD_GRP_179",
            "TRD_GRP_180",
            "TRD_GRP_181",
            "TRD_GRP_182",
            "TRD_GRP_183",
            "TRD_GRP_184"
          ]
        ],
        "defaultSelfTradePreventionMode": "EXPIRE_MAKER",
        "allowedSelfTradePreventionModes": [
          "EXPIRE_TAKER",
          "EXPIRE_MAKER",
          "EXPIRE_BOTH"
        ]
      },
      "tierBased": false,
      "percentage": true,
      "feeSide": "get"
    },
    """

    info: BinanceMarketInfo
    feeSide: str
