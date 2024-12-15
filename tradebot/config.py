from dataclasses import dataclass
from typing import Dict, List
from tradebot.constants import AccountType, ExchangeType
from tradebot.core.entity import RateLimit
from tradebot.strategy import Strategy
from tradebot.exchange.bybit import BybitAccountType
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

@dataclass
class PrivateConnectorConfig:
    account_type: AccountType
    rate_limit: RateLimit | None = None
    
@dataclass
class ZeroMQSignalConfig:
    """
    Custom signal config
    socket: zmq.asyncio.Socket
    
    ```
    from zmq.asyncio import Context
    
    context = Context()
    socket = context.socket(zmq.SUB)
    socket.connect("ipc:///tmp/zmq_custom_signal")
    
    # Subscribe to all messages
    socket.setsockopt(zmq.SUBSCRIBE, b"")
    ```
    
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



def main():
    config = Config(
        strategy_id="STRATEGY_ID",
        user_id="USER_ID",
        basic_config={
            ExchangeType.BYBIT: BasicConfig(
                exchange_id=ExchangeType.BYBIT,
                api_key="BYBIT_API_KEY",
                secret="BYBIT_SECRET",
                sandbox=True,
            )
        },
        public_conn_config={
            ExchangeType.BYBIT: [
                PublicConnectorConfig(
                    account_type=BybitAccountType.SPOT,
                )
            ]
        },
        private_conn_config={
            ExchangeType.BYBIT: [
                PrivateConnectorConfig(
                    account_type=BybitAccountType.SPOT,
                )
            ]
        },
    )

    print(config)


if __name__ == "__main__":
    main()
