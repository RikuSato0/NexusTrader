from typing import Any, Dict, List
from typing import Literal, Optional
from decimal import Decimal

from nexustrader.schema import Order


def in_orders(orders: List[Order], method: str, params: Dict[str, Any]) -> bool:
    for order in orders:
        match method:
            case "place_limit_order":
                if (
                    order.symbol == params["symbol"]
                    and order.side == params["side"]
                    and order.amount == params["amount"]
                    and order.price == params["price"]
                    and order.type == "limit"
                ):
                    return True
            case "place_market_order":
                if (
                    order.symbol == params["symbol"]
                    and order.side == params["side"]
                    and order.amount == params["amount"]
                    and order.type == "market"
                ):
                    return True
            case "cancel_order":
                if (
                    order.symbol == params["symbol"]
                    and order.id == params["id"]
                    and order.status == "canceled"
                ):
                    return True


def parse_ccxt_order(res: Dict[str, Any], exchange: str) -> Order:
    raw = res.get("info", {})
    id = res.get("id", None)
    client_order_id = res.get("clientOrderId", None)
    timestamp = res.get("timestamp", None)
    symbol = res.get("symbol", None)
    type = res.get("type", None)  # market or limit
    side = res.get("side", None)  # buy or sell
    price = res.get("price", None)  # maybe empty for market order
    average = res.get("average", None)  # float everage filling price
    amount = res.get("amount", None)
    filled = res.get("filled", None)
    remaining = res.get("remaining", None)
    status = raw.get("status", None).lower()
    cost = res.get("cost", None)
    reduce_only = raw.get("reduceOnly", None)
    position_side = raw.get("positionSide", "").lower() or None  # long or short
    time_in_force = res.get("timeInForce", None)

    return Order(
        raw=raw,
        success=True,
        exchange=exchange,
        id=id,
        client_order_id=client_order_id,
        timestamp=timestamp,
        symbol=symbol,
        type=type,
        side=side,
        price=price,
        average=average,
        amount=amount,
        filled=filled,
        remaining=remaining,
        status=status,
        cost=cost,
        reduce_only=reduce_only,
        position_side=position_side,
        time_in_force=time_in_force,
    )


def parse_websocket_stream(
    event_data: Dict[str, Any],
    market_id: Dict[str, Any],
    market_type: Optional[Literal["spot", "swap"]] = None,
):
    event = event_data.get("e", None)
    match event:
        case "kline":
            """
            {
                'e': 'kline', 
                'E': 1727525244267, 
                's': 'BTCUSDT', 
                'k': {
                    't': 1727525220000, 
                    'T': 1727525279999, 
                    's': 'BTCUSDT', 
                    'i': '1m', 
                    'f': 5422081499, 
                    'L': 5422081624, 
                    'o': '65689.80', 
                    'c': '65689.70', 
                    'h': '65689.80', 
                    'l': '65689.70', 
                    'v': '9.027', 
                    'n': 126, 
                    'x': False, 
                    'q': '592981.58290', 
                    'V': '6.610', 
                    'Q': '434209.57800', 
                    'B': '0'
                }
            }
            """
            id = f"{event_data['s']}_{market_type}" if market_type else event_data["s"]
            market = market_id[id]
            event_data["s"] = market["symbol"]
            return event_data


def parse_user_data_stream(event_data: Dict[str, Any], market_id: Dict[str, Any]):
    event = event_data.get("e", None)
    match event:
        case "ORDER_TRADE_UPDATE":
            """
            {
                "e": "ORDER_TRADE_UPDATE", // Event type
                "T": 1727352962757,  // Transaction time
                "E": 1727352962762, // Event time
                "fs": "UM", // Event business unit. 'UM' for USDS-M futures and 'CM' for COIN-M futures
                "o": {
                    "s": "NOTUSDT", // Symbol
                    "c": "c-11WLU7VP1727352880uzcu2rj4ss0i", // Client order ID
                    "S": "SELL", // Side
                    "o": "LIMIT", // Order type
                    "f": "GTC", // Time in force
                    "q": "5488", // Original quantity
                    "p": "0.0084830", // Original price
                    "ap": "0", // Average price
                    "sp": "0", // Ignore
                    "x": "NEW", // Execution type
                    "X": "NEW", // Order status
                    "i": 4968510801, // Order ID
                    "l": "0", // Order last filled quantity
                    "z": "0", // Order filled accumulated quantity
                    "L": "0", // Last filled price
                    "n": "0", // Commission, will not be returned if no commission
                    "N": "USDT", // Commission asset, will not be returned if no commission
                    "T": 1727352962757, // Order trade time
                    "t": 0, // Trade ID
                    "b": "0", // Bids Notional
                    "a": "46.6067521", // Ask Notional
                    "m": false, // Is this trade the maker side?
                    "R": false, // Is this reduce only
                    "ps": "BOTH", // Position side
                    "rp": "0", // Realized profit of the trade
                    "V": "EXPIRE_NONE", // STP mode
                    "pm": "PM_NONE", 
                    "gtd": 0
                }
            }
            """
            if event_data := event_data.get("o", None):
                if (market := market_id.get(event_data["s"], None)) is None:
                    id = f"{event_data['s']}_swap"
                    market = market_id[id]

                if (type := event_data["o"].lower()) == "market":
                    cost = float(event_data.get("l", "0")) * float(
                        event_data.get("ap", "0")
                    )
                elif type == "limit":
                    price = float(event_data.get("ap", "0")) or float(
                        event_data.get("p", "0")
                    )  # if average price is 0 or empty, use price
                    cost = float(event_data.get("l", "0")) * price

                return Order(
                    raw=event_data,
                    success=True,
                    exchange="binance",
                    id=event_data.get("i", None),
                    client_order_id=event_data.get("c", None),
                    timestamp=event_data.get("T", None),
                    symbol=market["symbol"],
                    type=type,
                    side=event_data.get("S", "").lower(),
                    status=event_data.get("X", "").lower(),
                    price=event_data.get("p", None),
                    average=event_data.get("ap", None),
                    last_filled_price=event_data.get("L", None),
                    amount=event_data.get("q", None),
                    filled=event_data.get("z", None),
                    last_filled=event_data.get("l", None),
                    remaining=Decimal(event_data["q"]) - Decimal(event_data["z"]),
                    fee=event_data.get("n", None),
                    fee_currency=event_data.get("N", None),
                    cost=cost,
                    last_trade_timestamp=event_data.get("T", None),
                    reduce_only=event_data.get("R", None),
                    position_side=event_data.get("ps", "").lower(),
                    time_in_force=event_data.get("f", None),
                )

        case "ACCOUNT_UPDATE":
            """
            {
                "e": "ACCOUNT_UPDATE", 
                "T": 1727352914268, 
                "E": 1727352914274, 
                "fs": "UM", 
                "a": {
                    "B": [
                        {"a": "USDT", "wb": "0.07147421", "cw": "0.07147421", "bc": "0"}, 
                        {"a": "BNB", "wb": "0.01993701", "cw": "0.01993701", "bc": "0"}
                    ], 
                    "P": [
                        {
                            "s": "BOMEUSDT", 
                            "pa": "-2760", 
                            "ep": "0.00724500", 
                            "cr": "0", 
                            "up": "-0.00077280", 
                            "ps": "BOTH", 
                            "bep": 0.0072436959
                        }
                    ], 
                "m": "ORDER"
                }
            }
            """
            positions = []
            for position in event_data["a"]["P"]:
                if (market := market_id.get(position["s"], None)) is None:
                    id = f"{position['s']}_swap"
                    market = market_id[id]
                position["s"] = market["symbol"]
                positions.append(position)
            event_data["a"]["P"] = positions
            return event_data

        case "balanceUpdate":
            """
            {
                "e": "balanceUpdate", 
                "E": 1727320813969, 
                "a": "BNB", 
                "d": "-0.01000000", 
                "U": 1495297874797, 
                "T": 1727320813969
            }
            """
            return event_data

        case "executionReport":
            """
            {
                "e": "executionReport", // Event type
                "E": 1727353057267, // Event time
                "s": "ORDIUSDT", // Symbol
                "c": "c-11WLU7VP2rj4ss0i", // Client order ID 
                "S": "BUY", // Side
                "o": "MARKET", // Order type
                "f": "GTC", // Time in force
                "q": "0.50000000", // Order quantity
                "p": "0.00000000", // Order price
                "P": "0.00000000", // Stop price
                "g": -1, // Order list id
                "x": "TRADE", // Execution type
                "X": "PARTIALLY_FILLED", // Order status
                "i": 2233880350, // Order ID
                "l": "0.17000000", // last executed quantity
                "z": "0.17000000", // Cumulative filled quantity
                "L": "36.88000000", // Last executed price
                "n": "0.00000216", // Commission amount
                "N": "BNB", // Commission asset
                "T": 1727353057266, // Transaction time
                "t": 105069149, // Trade ID
                "w": false, // Is the order on the book?
                "m": false, // Is this trade the maker side?
                "O": 1727353057266, // Order creation time
                "Z": "6.26960000", // Cumulative quote asset transacted quantity
                "Y": "6.26960000", // Last quote asset transacted quantity (i.e. lastPrice * lastQty)
                "V": "EXPIRE_MAKER", // Self trade prevention Mode
                "I": 1495839281094 // Ignore
            }
            
            # Example of an execution report event for a partially filled market buy order
            {
                "e": "executionReport", // Event type
                "E": 1727353057267, // Event time
                "s": "ORDIUSDT", // Symbol
                "c": "c-11WLU7VP2rj4ss0i", // Client order ID 
                "S": "BUY", // Side
                "o": "MARKET", // Order type
                "f": "GTC", // Time in force
                "q": "0.50000000", // Order quantity
                "p": "0.00000000", // Order price
                "P": "0.00000000", // Stop price
                "g": -1, // Order list id
                "x": "TRADE", // Execution type
                "X": "PARTIALLY_FILLED", // Order status
                "i": 2233880350, // Order ID
                "l": "0.17000000", // last executed quantity
                "z": "0.34000000", // Cumulative filled quantity
                "L": "36.88000000", // Last executed price
                "n": "0.00000216", // Commission amount
                "N": "BNB", // Commission asset
                "T": 1727353057266, // Transaction time
                "t": 105069150, // Trade ID
                "w": false, // Is the order on the book?
                "m": false, // Is this trade the maker side?
                "O": 1727353057266, // Order creation time
                "Z": "12.53920000", // Cumulative quote asset transacted quantity
                "Y": "6.26960000", // Last quote asset transacted quantity (i.e. lastPrice * lastQty)
                "V": "EXPIRE_MAKER", // Self trade prevention Mode
                "I": 1495839281094 // Ignore
            }
            
            """
            id = f"{event_data['s']}_spot"
            market = market_id[id]

            return Order(
                raw=event_data,
                success=True,
                exchange="binance",
                id=event_data.get("i", None),
                client_order_id=event_data.get("c", None),
                timestamp=event_data.get("T", None),
                symbol=market["symbol"],
                type=event_data.get("o", "").lower(),
                side=event_data.get("S", "").lower(),
                status=event_data.get("X", "").lower(),
                price=event_data.get("p", None),
                average=event_data.get("ap", None),
                last_filled_price=event_data.get("L", None),
                amount=event_data.get("q", None),
                filled=event_data.get("z", None),
                last_filled=event_data.get("l", None),
                remaining=Decimal(event_data.get("q", "0"))
                - Decimal(event_data.get("z", "0")),
                fee=event_data.get("n", None),
                fee_currency=event_data.get("N", None),
                cost=event_data.get("Y", None),
                last_trade_timestamp=event_data.get("T", None),
                time_in_force=event_data.get("f", None),
            )

        case "outboundAccountPosition":
            """
            {
                "e": "outboundAccountPosition", 
                "E": 1727353873873, 
                "u": 1727353873873, 
                "U": 1495859325408, 
                "B": [
                    {
                        "a": "BNB", 
                        "f": 
                        "0.09971173", 
                        "l": 
                        "0.00000000"
                    }, 
                    {
                        "a": "USDT", 
                        "f": "6426.31521496", 
                        "l": "0.00000000"
                    }, 
                    {"a": 
                    "AVAX", 
                    "f": "3.00000000", 
                    "l": "0.00000000"
                    }
                ]
            }
            """
            return event_data
