import pytest
import asyncio


from unittest.mock import AsyncMock, patch
from tradebot.exchange import OkxWebsocketManager



@pytest.fixture
async def okx_ws_manager():
    config = {
        "apiKey": "test_api_key",
        "secret": "test_secret",
        "passphrase": "test_passphrase"
    }
    manager = OkxWebsocketManager(config)
    yield manager
    await manager.close()

@pytest.mark.asyncio
async def test_subscribe(okx_ws_manager):
    okx_ws_manager = await okx_ws_manager.__anext__()
    callback = AsyncMock()

    with patch.object(OkxWebsocketManager, '_subscribe', new_callable=AsyncMock) as mock_subscribe:
        mock_subscribe.side_effect = lambda symbol, typ, channel, queue_id: asyncio.create_task(
            okx_ws_manager.queues[queue_id].put({"test": "data"})
        )

        symbols = ["BTC/USDT", "ETH/USDT"]
        await okx_ws_manager.subscribe(symbols, "spot", "trades", callback)

        await asyncio.sleep(0.1)

        assert mock_subscribe.call_count == 2
        mock_subscribe.assert_any_call("BTC/USDT", "spot", "trades", "BTC/USDT_spot_trades")
        mock_subscribe.assert_any_call("ETH/USDT", "spot", "trades", "ETH/USDT_spot_trades")

        assert callback.call_count == 2
        callback.assert_any_call({"test": "data"})

        assert len(okx_ws_manager.queues) == 2
        assert len(okx_ws_manager.tasks) == 4  # 2 for consume, 2 for _subscribe
