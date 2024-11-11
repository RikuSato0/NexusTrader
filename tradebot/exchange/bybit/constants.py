from tradebot.constants import (
    AccountType,
    OrderStatus,
    PositionSide,
    OrderSide,
    TimeInForce,
    OrderType,
)
from enum import Enum


class BybitAccountType(AccountType):
    SPOT = "SPOT"
    LINEAR = "LINEAR"
    INVERSE = "INVERSE"
    OPTION = "OPTION"
    SPOT_TESTNET = "SPOT_TESTNET"
    LINEAR_TESTNET = "LINEAR_TESTNET"
    INVERSE_TESTNET = "INVERSE_TESTNET"
    OPTION_TESTNET = "OPTION_TESTNET"

    @property
    def is_testnet(self):
        return self in {
            self.SPOT_TESTNET,
            self.LINEAR_TESTNET,
            self.INVERSE_TESTNET,
            self.OPTION_TESTNET,
        }

    @property
    def ws_public_url(self):
        return WS_PUBLIC_URL[self]

    @property
    def ws_private_url(self):
        if self.is_testnet:
            return "wss://stream-testnet.bybit.com/v5/private"
        return "wss://stream.bybit.com/v5/private"

    @property
    def is_spot(self):
        return self in {self.SPOT, self.SPOT_TESTNET}

    @property
    def is_linear(self):
        return self in {self.LINEAR, self.LINEAR_TESTNET}

    @property
    def is_inverse(self):
        return self in {self.INVERSE, self.INVERSE_TESTNET}


WS_PUBLIC_URL = {
    BybitAccountType.SPOT: "wss://stream.bybit.com/v5/public/spot",
    BybitAccountType.LINEAR: "wss://stream.bybit.com/v5/public/linear",
    BybitAccountType.INVERSE: "wss://stream.bybit.com/v5/public/inverse",
    BybitAccountType.OPTION: "wss://stream.bybit.com/v5/public/option",
    BybitAccountType.SPOT_TESTNET: "wss://stream-testnet.bybit.com/v5/public/spot",
    BybitAccountType.LINEAR_TESTNET: "wss://stream-testnet.bybit.com/v5/public/linear",
    BybitAccountType.INVERSE_TESTNET: "wss://stream-testnet.bybit.com/v5/public/inverse",
    BybitAccountType.OPTION_TESTNET: "wss://stream-testnet.bybit.com/v5/public/option",
}


class BybitBaseUrl(Enum):
    MAINNET_1 = "https://api.bybit.com"
    MAINNET_2 = "https://api.bytick.com"
    TESTNET = "https://api-testnet.bybit.com"
    NETHERLAND = "https://api.bybit.nl"
    HONGKONG = "https://api.byhkbit.com"
    TURKEY = "https://api.bybit-tr.com"
    HAZAKHSTAN = "https://api.bybit.kz"


class BybitOrderSide(Enum):
    BUY = "Buy"
    SELL = "Sell"


class BybitOrderStatus(Enum):
    NEW = "New"
    REJECTED = "Rejected"
    PARTIALLY_FILLED = "PartiallyFilled"
    PARTIALLY_FILLED_CANCELED = "PartiallyFilledCanceled"
    FILLED = "Filled"
    CANCELED = "Cancelled"
    UNTRIGGERED = "Untriggered"
    TRIGGERED = "Triggered"
    UNTRIGGERED = "Untriggered"
    DEACTIVATED = "Deactivated"


class BybitTimeInForce(Enum):
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"
    POST_ONLY = "PostOnly"


class BybitPositionSide(Enum):
    FLAT = 0
    LONG = 1
    SHORT = 2


class BybitOrderType(Enum):
    MARKET = "Market"
    LIMIT = "Limit"
    UNKNOWN = "Unknown"


class BybitProductType(Enum):
    SPOT = "spot"
    LINEAR = "linear"
    INVERSE = "inverse"
    OPTION = "option"


class BybitTriggerType(Enum):
    NONE = ""  # Default
    LAST_PRICE = "LastPrice"
    INDEX_PRICE = "IndexPrice"
    MARK_PRICE = "MarkPrice"


class BybitTriggerDirection(Enum):
    NONE = 0
    RISES_TO = 1  # Triggered when market price rises to triggerPrice
    FALLS_TO = 2


class BybitStopOrderType(Enum):
    NONE = ""  # Default
    UNKNOWN = "UNKNOWN"  # Classic account value
    TAKE_PROFIT = "TakeProfit"
    STOP_LOSS = "StopLoss"
    TRAILING_STOP = "TrailingStop"
    STOP = "Stop"
    PARTIAL_TAKE_PROFIT = "PartialTakeProfit"
    PARTIAL_STOP_LOSS = "PartialStopLoss"
    TPSL_ORDER = "tpslOrder"
    OCO_ORDER = "OcoOrder"  # Spot only
    MM_RATE_CLOSE = "MmRateClose"
    BIDIRECTIONAL_TPSL_ORDER = "BidirectionalTpslOrder"


class BybitEnumParser:
    _bybit_order_status_map = {
        BybitOrderStatus.NEW: OrderStatus.ACCEPTED,
        BybitOrderStatus.PARTIALLY_FILLED: OrderStatus.PARTIALLY_FILLED,
        BybitOrderStatus.FILLED: OrderStatus.FILLED,
        BybitOrderStatus.CANCELED: OrderStatus.CANCELED,
        BybitOrderStatus.TRIGGERED: OrderStatus.ACCEPTED,
        BybitOrderStatus.UNTRIGGERED: OrderStatus.PENDING,
        BybitOrderStatus.DEACTIVATED: OrderStatus.EXPIRED,
        BybitOrderStatus.REJECTED: OrderStatus.FAILED,
    }

    _bybit_position_side_map = {
        BybitPositionSide.FLAT: PositionSide.FLAT,
        BybitPositionSide.LONG: PositionSide.LONG,
        BybitPositionSide.SHORT: PositionSide.SHORT,
    }

    _bybit_order_side_map = {
        BybitOrderSide.BUY: OrderSide.BUY,
        BybitOrderSide.SELL: OrderSide.SELL,
    }

    _bybit_order_time_in_force_map = {
        BybitTimeInForce.IOC: TimeInForce.IOC,
        BybitTimeInForce.GTC: TimeInForce.GTC,
        BybitTimeInForce.FOK: TimeInForce.FOK,
    }

    _bybit_order_type_map = {
        BybitOrderType.MARKET: OrderType.MARKET,
        BybitOrderType.LIMIT: OrderType.LIMIT,
    }

    # Add reverse mapping dictionaries
    _order_status_to_bybit_map = {v: k for k, v in _bybit_order_status_map.items()}
    _position_side_to_bybit_map = {v: k for k, v in _bybit_position_side_map.items()}
    _order_side_to_bybit_map = {v: k for k, v in _bybit_order_side_map.items()}
    _time_in_force_to_bybit_map = {
        v: k for k, v in _bybit_order_time_in_force_map.items()
    }
    _order_type_to_bybit_map = {
        v: k for k, v in _bybit_order_type_map.items() if v is not None
    }

    # Add reverse parsing methods
    @classmethod
    def parse_order_status(cls, status: BybitOrderStatus) -> OrderStatus:
        return cls._bybit_order_status_map[status]

    @classmethod
    def parse_position_side(cls, side: BybitPositionSide) -> PositionSide:
        return cls._bybit_position_side_map[side]

    @classmethod
    def parse_order_side(cls, side: BybitOrderSide) -> OrderSide:
        return cls._bybit_order_side_map[side]

    @classmethod
    def parse_time_in_force(cls, tif: BybitTimeInForce) -> TimeInForce:
        return cls._bybit_order_time_in_force_map[tif]

    @classmethod
    def parse_order_type(cls, order_type: BybitOrderType) -> OrderType:
        return cls._bybit_order_type_map[order_type]

    @classmethod
    def to_bybit_order_status(cls, status: OrderStatus) -> BybitOrderStatus:
        return cls._order_status_to_bybit_map[status]

    @classmethod
    def to_bybit_position_side(cls, side: PositionSide) -> BybitPositionSide:
        return cls._position_side_to_bybit_map[side]

    @classmethod
    def to_bybit_order_side(cls, side: OrderSide) -> BybitOrderSide:
        return cls._order_side_to_bybit_map[side]

    @classmethod
    def to_bybit_time_in_force(cls, tif: TimeInForce) -> BybitTimeInForce:
        return cls._time_in_force_to_bybit_map[tif]

    @classmethod
    def to_bybit_order_type(cls, order_type: OrderType) -> BybitOrderType:
        return cls._order_type_to_bybit_map[order_type]
