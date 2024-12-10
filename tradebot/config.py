from dataclasses import dataclass
from typing import Dict, List
from tradebot.constants import AccountType, ExchangeType
from tradebot.exchange.bybit import BybitAccountType

@dataclass
class BasicConfig:
    exchange_id: ExchangeType
    api_key: str
    secret: str
    sandbox: bool = False
    passphrase: str = None

@dataclass
class PublicConnectorConfig:
    account_type: AccountType
    symbols: List[str]

@dataclass
class PrivateConnectorConfig:
    account_type: AccountType
    rate_limit: float = None

@dataclass
class Config:
    strategy_id: str
    user_id: str
    basic_config: Dict[ExchangeType, BasicConfig]
    public_conn_config: Dict[ExchangeType, List[PublicConnectorConfig]]
    private_conn_config: Dict[ExchangeType, PrivateConnectorConfig]

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
                    symbols=["BTCUSDT.BYBIT", "ETHUSDT.BYBIT"],
                )
            ]
        },
        private_conn_config={
            ExchangeType.BYBIT: PrivateConnectorConfig(
                account_type=BybitAccountType.SPOT,
            )
        },
    )

    print(config)


if __name__ == "__main__":
    main()
