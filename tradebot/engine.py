import asyncio
import platform
from typing import Dict, Set
from tradebot.constants import AccountType, ExchangeType
from tradebot.config import Config
from tradebot.strategy import Strategy
from tradebot.core.cache import AsyncCache
from tradebot.core.oms import OrderManagerSystem
from tradebot.base import ExchangeManager, PublicConnector, PrivateConnector
from tradebot.exchange.bybit import (
    BybitExchangeManager,
    BybitPrivateConnector,
    BybitPublicConnector,
    BybitAccountType,
)
from tradebot.exchange.binance import BinanceExchangeManager
from tradebot.exchange.okx import OkxExchangeManager
from tradebot.core.entity import TaskManager
from tradebot.core.nautilius_core import MessageBus, TraderId, LiveClock
from tradebot.types import InstrumentId
from tradebot.constants import DataType, InstrumentType


class Engine:
    @staticmethod
    def set_loop_policy():
        if platform.system() != "Windows":
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    def __init__(self, config: Config):
        self._config = config
        self._is_running = False
        self._is_built = False
        self.set_loop_policy()
        self._loop = asyncio.new_event_loop()
        self._task_manager = TaskManager(self._loop)

        self._exchanges: Dict[ExchangeType, ExchangeManager] = {}
        self._public_connectors: Dict[AccountType, PublicConnector] = {}
        self._private_connectors: Dict[AccountType, PrivateConnector] = {}

        trader_id = f"{self._config.strategy_id}-{self._config.user_id}"

        self._cache: AsyncCache = AsyncCache(
            strategy_id=config.strategy_id,
            user_id=config.user_id,
            task_manager=self._task_manager,
            sync_interval=config.cache_sync_interval,
            expire_time=config.cache_expire_time,
        )

        self._msgbus = MessageBus(
            trader_id=TraderId(trader_id),
            clock=LiveClock(),
        )

        self._oms = OrderManagerSystem(
            cache=self._cache,
            msgbus=self._msgbus,
            task_manager=self._task_manager,
        )

        self._strategy: Strategy = config.strategy
        self._strategy._init_core(msgbus=self._msgbus, task_manager=self._task_manager)

        self._subscriptions: Dict[
            DataType, Dict[str, str] | Set[str]
        ] = self._strategy._subscriptions

    def _build_public_connectors(self):
        for exchange_id, public_conn_configs in self._config.public_conn_config.items():
            for config in public_conn_configs:
                if exchange_id == ExchangeType.BYBIT:
                    exchange: BybitExchangeManager = self._exchanges[exchange_id]
                    account_type: BybitAccountType = config.account_type
                    public_connector = BybitPublicConnector(
                        account_type=account_type,
                        exchange=exchange,
                        msgbus=self._msgbus,
                        task_manager=self._task_manager,
                    )
                    if (
                        self._config.basic_config[exchange_id].testnet
                        != account_type.is_testnet
                    ):
                        raise ValueError(
                            f"The `testnet` setting of {exchange_id} is not consistent with the public connector's account type `{account_type}`."
                        )
                    self._public_connectors[account_type] = public_connector

                elif exchange_id == ExchangeType.BINANCE:
                    pass
                elif exchange_id == ExchangeType.OKX:
                    pass

                self._public_connectors[config.account_type] = public_connector

    def _build_private_connectors(self):
        for (
            exchange_id,
            private_conn_configs,
        ) in self._config.private_conn_config.items():
            if exchange_id == ExchangeType.BYBIT:
                config = private_conn_configs[0]
                exchange: BybitExchangeManager = self._exchanges[exchange_id]

                account_type = (
                    BybitAccountType.ALL_TESTNET
                    if exchange.is_testnet
                    else BybitAccountType.ALL
                )

                private_connector = BybitPrivateConnector(
                    exchange=exchange,
                    account_type=account_type,
                    msgbus=self._msgbus,
                    rate_limit=config.rate_limit,
                    task_manager=self._task_manager,
                )
                self._private_connectors[account_type] = private_connector
                continue

            for config in private_conn_configs:
                if exchange_id == ExchangeType.BINANCE:
                    pass
                elif exchange_id == ExchangeType.OKX:
                    pass

    def _build_exchanges(self):
        for exchange_id, basic_config in self._config.basic_config.items():
            config = {
                "apiKey": basic_config.api_key,
                "secret": basic_config.secret,
                "sandbox": basic_config.testnet,
            }
            if basic_config.passphrase:
                config["password"] = basic_config.passphrase

            if exchange_id == ExchangeType.BYBIT:
                self._exchanges[exchange_id] = BybitExchangeManager(config)
            elif exchange_id == ExchangeType.BINANCE:
                self._exchanges[exchange_id] = BinanceExchangeManager(config)
            elif exchange_id == ExchangeType.OKX:
                self._exchanges[exchange_id] = OkxExchangeManager(config)

    def _build(self):
        self._build_exchanges()
        self._build_public_connectors()
        self._build_private_connectors()
        self._is_built = True

    def _instrument_id_to_account_type(
        self, instrument_id: InstrumentId
    ) -> AccountType:
        match instrument_id.exchange:
            case ExchangeType.BYBIT:
                if instrument_id.type == InstrumentType.SPOT:
                    return (
                        BybitAccountType.SPOT_TESTNET
                        if self._config.basic_config[ExchangeType.BYBIT].testnet
                        else BybitAccountType.SPOT
                    )
                elif instrument_id.type == InstrumentType.LINEAR:
                    return (
                        BybitAccountType.LINEAR_TESTNET
                        if self._config.basic_config[ExchangeType.BYBIT].testnet
                        else BybitAccountType.LINEAR
                    )
                elif instrument_id.type == InstrumentType.INVERSE:
                    return (
                        BybitAccountType.INVERSE_TESTNET
                        if self._config.basic_config[ExchangeType.BYBIT].testnet
                        else BybitAccountType.INVERSE
                    )
                else:
                    raise ValueError(
                        f"Unsupported instrument type: {instrument_id.type}"
                    )
            case ExchangeType.BINANCE:
                pass
            case ExchangeType.OKX:
                pass

    async def _start_connectors(self):
        for data_type, sub in self._subscriptions.items():
            match data_type:
                case DataType.BOOKL1:
                    for symbol in sub:
                        instrument_id = InstrumentId.from_str(symbol)
                        account_type = self._instrument_id_to_account_type(
                            instrument_id
                        )
                        connector = self._public_connectors.get(account_type, None)
                        if connector is None:
                            raise ValueError(
                                f"Please add `{account_type}` public connector to the `config.public_conn_config`."
                            )
                        await connector.subscribe_bookl1(instrument_id.symbol)
                case DataType.TRADE:
                    for symbol in sub:
                        instrument_id = InstrumentId.from_str(symbol)
                        account_type = self._instrument_id_to_account_type(
                            instrument_id
                        )
                        connector = self._public_connectors.get(account_type, None)
                        if connector is None:
                            raise ValueError(
                                f"Please add `{account_type}` public connector to the `config.public_conn_config`."
                            )
                        await connector.subscribe_trade(instrument_id.symbol)
                case DataType.KLINE:
                    for symbol, interval in sub.items():
                        instrument_id = InstrumentId.from_str(symbol)
                        account_type = self._instrument_id_to_account_type(
                            instrument_id
                        )
                        connector = self._public_connectors.get(account_type, None)
                        if connector is None:
                            raise ValueError(
                                f"Please add `{account_type}` public connector to the `config.public_conn_config`."
                            )
                        await connector.subscribe_kline(instrument_id.symbol, interval)
                case DataType.MARK_PRICE:
                    pass  # TODO: implement
                case DataType.FUNDING_RATE:
                    pass  # TODO: implement
                case DataType.INDEX_PRICE:
                    pass  # TODO: implement

        for connector in self._private_connectors.values():
            await connector.connect()

    async def _start(self):
        await self._cache.start()
        await self._oms.start()
        await self._start_connectors()
        await self._task_manager.wait()

    async def _dispose(self):
        for connector in self._public_connectors.values():
            await connector.disconnect()
        for connector in self._private_connectors.values():
            await connector.disconnect()
        await self._task_manager.cancel()

    def start(self):
        self._build()
        self._is_running = True
        self._loop.run_until_complete(self._start())

    def dispose(self):
        self._loop.run_until_complete(self._dispose())
        self._loop.close()
