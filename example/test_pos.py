import re
from tradebot.types import Position, Order
from typing import Dict
from tqdm import tqdm
import re
import orjson
from typing import Optional, Dict, Any
from decimal import Decimal
import msgspec
from tradebot.log import SpdLog

logger = SpdLog.get_logger(__name__, "INFO", flush=True)


def clean_enum_value(value: str) -> Optional[str]:
    """Clean enum values like <OrderStatus.PENDING: 'PENDING'> to just 'PENDING'"""
    if value == 'None':
        return None
    enum_match = re.search(r"<[^:]+:\s*'([^']+)'>", value)
    return enum_match.group(1) if enum_match else value

def clean_value(value: str) -> Any:
    """Clean numeric values, handling Decimal and None cases"""
    if value == 'None':
        return None
    try:
        if value.startswith('Decimal'):
            return float(re.search(r"Decimal\('([^']+)'\)", value).group(1))
        return float(value)
    except (ValueError, AttributeError):
        return value

def parse_order_log(order_str: str) -> Optional[Dict[str, Any]]:
    """Parse an Order string into a dictionary"""
    pattern = r"""Order\(
        exchange='(?P<exchange>[^']+)',\s*
        symbol='(?P<symbol>[^']+)',\s*
        status=<[^:]+:\s*'(?P<status>[^']+)'>,\s*
        id='(?P<id>[^']+)',\s*
        amount=(?P<amount>[^,]+),\s*
        filled=(?P<filled>[^,]+),\s*
        client_order_id='(?P<client_order_id>[^']*)',\s*
        timestamp=(?P<timestamp>\d+),\s*
        type=(?P<type>(?:<[^:]+:\s*'[^']+'>\s*|None)),\s*
        side=(?P<side>(?:<[^:]+:\s*'[^']+'>\s*|None)),\s*
        time_in_force=(?P<time_in_force>(?:<[^:]+:\s*'[^']+'>\s*|None)),\s*
        price=(?P<price>[^,]+),\s*
        average=(?P<average>[^,]+),\s*
        last_filled_price=(?P<last_filled_price>[^,]+),\s*
        last_filled=(?P<last_filled>[^,]+),\s*
        remaining=(?P<remaining>[^,]+),\s*
        fee=(?P<fee>[^,]+),\s*
        fee_currency='(?P<fee_currency>[^']*)',\s*
        cost=(?P<cost>[^,]+),\s*
        cum_cost=(?P<cum_cost>[^,]+),\s*
        reduce_only=(?P<reduce_only>[^,]+),\s*
        position_side=(?P<position_side>(?:<[^:]+:\s*'[^']+'>\s*|None))
    \)"""

    match = re.search(pattern, order_str, re.VERBOSE)
    if not match:
        return None
    
    order_dict = match.groupdict()
    
    # Clean enum values
    enum_fields = ['status', 'type', 'side', 'time_in_force', 'position_side']
    for field in enum_fields:
        order_dict[field] = clean_enum_value(order_dict[field])
    
    # Clean numeric values
    numeric_fields = ['amount', 'filled', 'price', 'average', 'last_filled_price', 
                     'last_filled', 'remaining', 'fee', 'cost', 'cum_cost']
    for field in numeric_fields:
        order_dict[field] = clean_value(order_dict[field])
    
    # Convert timestamp to int
    order_dict['timestamp'] = int(order_dict['timestamp'])
    
    # Handle boolean values
    if order_dict['reduce_only'] == 'False':
        order_dict['reduce_only'] = False
    elif order_dict['reduce_only'] == 'True':
        order_dict['reduce_only'] = True
    
    return order_dict

def parse_log_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a complete log line including timestamp and Order details"""
    log_pattern = r'\[(.*?)\] \[OrderManagerSystem\] \[debug\] ORDER STATUS .*?: (Order\(.*\))'
    match = re.search(log_pattern, line)
    if not match:
        return None
    
    _, order_str = match.groups()
    order_dict = parse_order_log(order_str)
    return order_dict

def process_log_file(log_content: str) -> list[Order]:
    """Process the entire log file and print results"""
    orders = []
    for line in tqdm(log_content.split('\n')):
        if line.strip():  # Skip empty lines
            result = parse_log_line(line)
            if result:
                result_json = orjson.dumps(result)
                order = msgspec.json.decode(result_json, type=Order)
                orders.append(order)
    return orders
        
def test_position_updates():
    # Read the log file
    with open('.log/OrderManagerSystem_2024-12-07.log', 'r') as f:
        log_content = f.read()
    
    # Extract relevant orders
    orders = process_log_file(log_content)
    
    # Initialize position dictionary
    pos_dict: Dict[str, Position] = {}
    
    # Process each order
    for order in orders:
        symbol = order.symbol
        
        # Initialize position if it doesn't exist
        if symbol not in pos_dict:
            pos_dict[symbol] = Position(
                symbol=symbol,
                exchange=order.exchange,
                strategy_id="test_strategy"
            )
        
        # Apply the order to position
        try:
            pos_dict[symbol].apply(order)
            
            # Print position status after each order
            pos = pos_dict[symbol]
            logger.info(f"\nApplied Order: {order.id} ({order.status})")
            logger.info("Position Status:")
            logger.info(f"  Symbol: {pos.symbol}")
            logger.info(f"  Side: {pos.side}")
            logger.info(f"  Signed Amount: {pos.signed_amount}")
            logger.info(f"  Entry Price: {pos.entry_price}")
            logger.info(f"  Unrealized PNL: {pos.unrealized_pnl}")
            logger.info(f"  Realized PNL: {pos.realized_pnl}")
            
        except Exception as e:
            logger.error(f"Error processing order {order.id}: {str(e)}")
            

if __name__ == "__main__":
    test_position_updates()
