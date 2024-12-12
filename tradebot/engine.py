import asyncio
import signal
import uvloop
from typing import Dict
from tradebot.constants import AccountType, ExchangeType
from tradebot.config import Config
from tradebot.strategy import Strategy
from tradebot.core.cache import AsyncCache
from tradebot.core.oms import OrderManagerSystem
from tradebot.base import ExchangeManager, PublicConnector, PrivateConnector
from tradebot.exchange.bybit import BybitExchangeManager, BybitPrivateConnector, BybitPublicConnector, BybitAccountType
from tradebot.exchange.binance import BinanceExchangeManager
from tradebot.exchange.okx import OkxExchangeManager

from tradebot.core.nautilius_core import MessageBus, TraderId, LiveClock

class Engine:
    def __init__(self, config: Config):
        self._config = config
        self._strategy = None
        self._is_running = False
        self._is_built = False
        self.loop = asyncio.get_event_loop()
        
        self._exchanges: Dict[ExchangeType, ExchangeManager] = None
        self._public_connectors: Dict[AccountType, PublicConnector] = None
        self._private_connectors: Dict[AccountType, PrivateConnector] = None
        
        trader_id = f"{self._config.strategy_id}-{self._config.user_id}"
        
        self._cache: AsyncCache = AsyncCache(
            strategy_id=config.strategy_id,
            user_id=config.user_id,
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
        )
    
    def _build_public_connectors(self):
        for exchange_id, public_conn_configs in self._config.public_conn_config.items():
            for config in public_conn_configs:
                if exchange_id == ExchangeType.BYBIT:
                    exchange: BybitExchangeManager = self._exchanges[exchange_id]
                    public_connector = BybitPublicConnector(
                        account_type=config.account_type,
                        exchange=exchange,
                        msgbus=self._msgbus,
                    )
                elif exchange_id == ExchangeType.BINANCE:
                    pass
                elif exchange_id == ExchangeType.OKX:
                    pass
                
                self._public_connectors[config.account_type] = public_connector
    
    def _build_private_connectors(self):
        for exchange_id, private_conn_configs in self._config.private_conn_config.items():
            if exchange_id == ExchangeType.BYBIT:
                config = private_conn_configs[0]
                exchange: BybitExchangeManager = self._exchanges[exchange_id]
                
                account_type = BybitAccountType.ALL_TESTNET if exchange.is_testnet else BybitAccountType.ALL
                
                private_connector = BybitPrivateConnector(
                    account_type=account_type,
                    exchange=exchange,
                    msgbus=self._msgbus,
                    strategy_id=self._config.strategy_id,
                    user_id=self._config.user_id,
                    rate_limit=config.rate_limit,
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
                "sandbox": basic_config.sandbox,
            }
            if basic_config.passphrase:
                config["password"] = basic_config.passphrase
            
            if exchange_id == ExchangeType.BYBIT:
                self._exchanges[exchange_id] = BybitExchangeManager(config)
            elif exchange_id == ExchangeType.BINANCE:
                self._exchanges[exchange_id] = BinanceExchangeManager(config)
            elif exchange_id == ExchangeType.OKX:
                self._exchanges[exchange_id] = OkxExchangeManager(config)
    
    
    def build(self):
        if self._is_built:
            raise RuntimeError("The engine is already built.")
        self._build_exchanges()
        self._build_public_connectors()
        self._build_private_connectors()
        self._is_built = True

    def start(self):
        if not self._is_built:
            raise RuntimeError("The engine is not built. Call `build()` first.")
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        self.loop = asyncio.get_event_loop()
        self._is_running = True
        self.loop.run_until_complete(self.run_async())

    async def run_async(self):
        try:
            tasks = [connector.connect() for connector in self.connectors]
            tasks += [strategy.run() for strategy in self.strategies]
            await asyncio.gather(*tasks)
        except asyncio.CancelledError as e:
            print(f"Cancelled: {e}")
