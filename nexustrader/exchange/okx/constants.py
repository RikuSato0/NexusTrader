from enum import Enum, unique
from nexustrader.constants import (
    AccountType,
    OrderStatus,
    PositionSide,
    OrderSide,
    TimeInForce,
    OrderType,
)


class OkxInstrumentType(Enum):
    SPOT = "SPOT"
    MARGIN = "MARGIN"
    SWAP = "SWAP"
    FUTURES = "FUTURES"
    OPTION = "OPTION"
    ANY = "ANY"

class OkxInstrumentFamily(Enum):
    FUTURES = "FUTURES"
    SWAP = "SWAP"
    OPTION = "OPTION"

class OkxAccountType(AccountType):
    LIVE = 0
    AWS = 1
    DEMO = 2
    
    @property
    def exchange_id(self):
        return "okx"

    @property
    def is_testnet(self):
        return self == OkxAccountType.DEMO
    
    @property
    def stream_url(self):
        return STREAM_URLS[self]


class OkxRestUrl(Enum):
    LIVE = "https://www.okx.com"
    AWS = "https://aws.okx.com"
    DEMO = "https://www.okx.com"


STREAM_URLS = {
    OkxAccountType.LIVE: "wss://ws.okx.com:8443/ws",
    OkxAccountType.AWS: "wss://wsaws.okx.com:8443/ws",
    OkxAccountType.DEMO: "wss://wspap.okx.com:8443/ws",
}

REST_URLS = {
    OkxAccountType.LIVE: "https://www.okx.com",
    OkxAccountType.AWS: "https://aws.okx.com",
    OkxAccountType.DEMO: "https://www.okx.com",
}


@unique
class OkxTdMode(Enum):
    CASH = "cash"  # 现货
    CROSS = "cross"  # 全仓
    ISOLATED = "isolated"  # 逐仓
    SPOT_ISOLATED = "spot_isolated"  # 现货逐仓


@unique
class OkxPositionSide(Enum):
    LONG = "long"
    SHORT = "short"
    NET = "net"
    NONE = ""

    def parse_to_position_side(self) -> PositionSide:
        if self == self.NET:
            return PositionSide.FLAT
        elif self == self.LONG:
            return PositionSide.LONG
        elif self == self.SHORT:
            return PositionSide.SHORT
        raise RuntimeError(f"Invalid position side: {self}")

@unique
class OkxOrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OkxTimeInForce(Enum):
    IOC = "ioc"
    GTC = "gtc"
    FOK = "fok"


@unique
class OkxOrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    POST_ONLY = "post_only"  # limit only, requires "px" to be provided
    FOK = "fok"  # market order if "px" is not provided, otherwise limit order
    IOC = "ioc"  # market order if "px" is not provided, otherwise limit order
    OPTIMAL_LIMIT_IOC = (
        "optimal_limit_ioc"  # Market order with immediate-or-cancel order
    )
    MMP = "mmp"  # Market Maker Protection (only applicable to Option in Portfolio Margin mode)
    MMP_AND_POST_ONLY = "mmp_and_post_only"  # Market Maker Protection and Post-only order(only applicable to Option in Portfolio Margin mode)


@unique
class OkxOrderStatus(Enum):  # "state"
    CANCELED = "canceled"
    LIVE = "live"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    MMP_CANCELED = "mmp_canceled"


class OkxEnumParser:
    _okx_order_status_map = {
        OkxOrderStatus.LIVE: OrderStatus.ACCEPTED,
        OkxOrderStatus.PARTIALLY_FILLED: OrderStatus.PARTIALLY_FILLED,
        OkxOrderStatus.FILLED: OrderStatus.FILLED,
        OkxOrderStatus.CANCELED: OrderStatus.CANCELED,
    }

    _okx_position_side_map = {
        OkxPositionSide.NET: PositionSide.FLAT,
        OkxPositionSide.LONG: PositionSide.LONG,
        OkxPositionSide.SHORT: PositionSide.SHORT,
        OkxPositionSide.NONE: None,
    }

    _okx_order_side_map = {
        OkxOrderSide.BUY: OrderSide.BUY,
        OkxOrderSide.SELL: OrderSide.SELL,
    }

    # Add reverse mapping dictionaries
    _order_status_to_okx_map = {v: k for k, v in _okx_order_status_map.items()}
    _position_side_to_okx_map = {
        PositionSide.FLAT: OkxPositionSide.NET,
        PositionSide.LONG: OkxPositionSide.LONG,
        PositionSide.SHORT: OkxPositionSide.SHORT,
    }
    _order_side_to_okx_map = {v: k for k, v in _okx_order_side_map.items()}

    # Add reverse parsing methods
    @classmethod
    def parse_order_status(cls, status: OkxOrderStatus) -> OrderStatus:
        return cls._okx_order_status_map[status]

    @classmethod
    def parse_position_side(cls, side: OkxPositionSide) -> PositionSide:
        return cls._okx_position_side_map[side]

    @classmethod
    def parse_order_side(cls, side: OkxOrderSide) -> OrderSide:
        return cls._okx_order_side_map[side]

    @classmethod
    def parse_order_type(cls, ordType: OkxOrderType) -> OrderType:
        # TODO add parameters in future to enable parsing of all other nautilus OrderType's
        match ordType:
            case OkxOrderType.MARKET:
                return OrderType.MARKET
            case OkxOrderType.LIMIT:
                return OrderType.LIMIT
            case OkxOrderType.IOC:
                return OrderType.LIMIT
            case OkxOrderType.FOK:
                return OrderType.LIMIT
            case OkxOrderType.POST_ONLY:
                return OrderType.LIMIT
            case _:
                raise NotImplementedError(
                    f"Cannot parse OrderType from OKX order type {ordType}"
                )

    @classmethod
    def parse_time_in_force(cls, ordType: OkxOrderType) -> TimeInForce:
        match ordType:
            case OkxOrderType.MARKET:
                return TimeInForce.GTC
            case OkxOrderType.LIMIT:
                return TimeInForce.GTC
            case OkxOrderType.POST_ONLY:
                return TimeInForce.GTC
            case OkxOrderType.FOK:
                return TimeInForce.FOK
            case OkxOrderType.IOC:
                return TimeInForce.IOC
            case _:
                raise NotImplementedError(
                    f"Cannot parse TimeInForce from OKX order type {ordType}"
                )

    @classmethod
    def to_okx_order_status(cls, status: OrderStatus) -> OkxOrderStatus:
        return cls._order_status_to_okx_map[status]

    @classmethod
    def to_okx_position_side(cls, side: PositionSide) -> OkxPositionSide:
        return cls._position_side_to_okx_map[side]

    @classmethod
    def to_okx_order_side(cls, side: OrderSide) -> OkxOrderSide:
        return cls._order_side_to_okx_map[side]

    @classmethod
    def to_okx_order_type(
        cls, order_type: OrderType, time_in_force: TimeInForce
    ) -> OkxOrderType:
        if order_type == OrderType.MARKET:
            return OkxOrderType.MARKET

        match time_in_force:
            case TimeInForce.GTC:
                return OkxOrderType.LIMIT  # OKX limit orders are GTC by default
            case TimeInForce.FOK:
                return OkxOrderType.FOK
            case TimeInForce.IOC:
                return OkxOrderType.IOC
            case _:
                raise RuntimeError(
                    f"Could not determine OKX order type from order_type {order_type} and time_in_force {time_in_force}, valid OKX order types are: {list(OkxOrderType)}",
                )
