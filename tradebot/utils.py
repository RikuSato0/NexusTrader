import ast
import ccxt
import json

from typing import Dict, Any
from typing import Generator, Optional, Literal


from tradebot.entity import Order



def parse_log_line(line) -> Optional[Dict]:
    try:
        # json_str = line.split("user data stream: ")[-1]
        return json.loads(line.strip())
    except:
        return None

def stream_generator(input_file: str) -> Generator[Optional[Dict], None, None]:
    with open(input_file, 'r') as f:
        for line in f:
            yield parse_log_line(line)


        
        