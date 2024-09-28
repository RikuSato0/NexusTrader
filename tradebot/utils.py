import ast
import ccxt
from typing import Dict, Any
from typing import Generator, Optional, Literal






def parse_log_line(line) -> Optional[Dict]:
    try:
        # json_str = line.split("user data stream: ")[-1]
        return ast.literal_eval(line)
    except:
        return None

def stream_generator(input_file: str) -> Generator[Optional[Dict], None, None]:
    with open(input_file, 'r') as f:
        for line in f:
            yield parse_log_line(line)

def parse_event_data(event_data: Dict[str, Any], market_id: Dict[str, Any], market_type: Optional[Literal["spot", "swap"]] = None):
    event = event_data.get('e', None)
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
            id = f"{event_data['s']}_{market_type}" if market_type else event_data['s']
            market = market_id[id]
            event_data['s'] = market['symbol']
            return event_data
        case "ORDER_TRADE_UPDATE":
            """
            {
                "e": "ORDER_TRADE_UPDATE", 
                "T": 1727352962757, 
                "E": 1727352962762, 
                "fs": "UM", 
                "o": {
                    "s": "NOTUSDT", 
                    "c": "c-11WLU7VP1727352880uzcu2rj4ss0i", 
                    "S": "SELL", 
                    "o": "LIMIT", 
                    "f": "GTC", 
                    "q": "5488", 
                    "p": "0.0084830", 
                    "ap": "0", 
                    "sp": "0", 
                    "x": "NEW", 
                    "X": "NEW", 
                    "i": 4968510801, 
                    "l": "0", 
                    "z": "0", 
                    "L": "0", 
                    "n": "0", 
                    "N": "USDT", 
                    "T": 1727352962757, 
                    "t": 0, 
                    "b": "0", 
                    "a": "46.6067521", 
                    "m": false, 
                    "R": false, 
                    "ps": "BOTH", 
                    "rp": "0", 
                    "V": "EXPIRE_NONE", 
                    "pm": "PM_NONE", 
                    "gtd": 0
                }
            }
            """
        
        
        