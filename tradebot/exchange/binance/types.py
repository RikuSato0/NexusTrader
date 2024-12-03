import msgspec
from typing import Any, Dict, List
from ...types import Order, BaseMarket
from ...constants import OrderSide, TimeInForce
from .constants import BinanceOrderStatus, BinanceOrderType, BinancePositionSide

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
    baseAssetPrecision: str = None
    quoteAsset: str = None
    quotePrecision: str = None
    quoteAssetPrecision: str = None
    baseCommissionPrecision: str = None
    quoteCommissionPrecision: str = None
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
    
    
