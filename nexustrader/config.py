from dataclasses import dataclass
from typing import Dict, List
from nexustrader.constants import AccountType, ExchangeType
from nexustrader.core.entity import RateLimit
from nexustrader.strategy import Strategy
from zmq.asyncio import Socket

@dataclass
class BasicConfig:
    api_key: str
    secret: str
    testnet: bool = False
    passphrase: str = None

@dataclass
class PublicConnectorConfig:
    account_type: AccountType
    rate_limit: RateLimit | None = None

@dataclass
class PrivateConnectorConfig:
    account_type: AccountType
    rate_limit: RateLimit | None = None
    
@dataclass
class ZeroMQSignalConfig:
    """ZeroMQ Signal Configuration Class.

    Used to configure the ZeroMQ subscriber socket to receive custom trade signals.

    Attributes:
        socket (`zmq.asyncio.Socket`): ZeroMQ asynchronous socket object

    Example:
        >>> from zmq.asyncio import Context
        >>> context = Context()
        >>> socket = context.socket(zmq.SUB)
        >>> socket.connect("ipc:///tmp/zmq_custom_signal")
        >>> socket.setsockopt(zmq.SUBSCRIBE, b"")
        >>> config = ZeroMQSignalConfig(socket=socket)
    """
    socket: Socket
    

@dataclass
class Config:
    strategy_id: str
    user_id: str
    strategy: Strategy
    basic_config: Dict[ExchangeType, BasicConfig]
    public_conn_config: Dict[ExchangeType, List[PublicConnectorConfig]]
    private_conn_config: Dict[ExchangeType, List[PrivateConnectorConfig]]
    zero_mq_signal_config: ZeroMQSignalConfig | None = None
    cache_sync_interval: int = 60
    cache_expire_time: int = 3600
