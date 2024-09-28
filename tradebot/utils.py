import ast
import ccxt


from typing import Dict, Any
from typing import Generator, Optional, Literal


from tradebot.entity import OrderResponse



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


        
        