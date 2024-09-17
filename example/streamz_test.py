# from streamz import Stream

# spot_source = Stream()
# future_source = Stream()

# def cal_ratio(value):
#     future, spot = value
#     if spot > 0 and future > 0:
#         return future / spot - 1
#     else:
#         return 0


# ratio = future_source.zip(spot_source).map(cal_ratio).sink(print)

# spot_source.emit(1)
# future_source.emit(2)
# future_source.emit(3)
# future_source.emit(4)
# spot_source.emit(2)

import json
import orjson
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, List, Optional

import websockets
from websockets.asyncio import client
from bytewax import operators as op
from bytewax.connectors.stdio import StdOutSink
from bytewax.dataflow import Dataflow
from bytewax.inputs import FixedPartitionedSource, StatefulSourcePartition, batch_async
import asynciolimiter
from bytewax.run import cli_main

limiter = asynciolimiter.Limiter(5 / 1)


async def _ws_gen(inst_id: str):
    params = [{
        "channel": "bbo-tbt",
        "instId": inst_id
    }]
    await limiter.wait()
    async with client.connect(
            uri="wss://ws.okx.com:8443/ws/v5/public",
            ping_interval=5,
            ping_timeout=5,
            close_timeout=5,
            max_queue=12,
    ) as ws:
        payload = json.dumps({
            "op": "subscribe",
            "args": params
        })
        await ws.send(payload)
        await ws.recv()  # subscription msg
        async for msg in ws:
            yield (inst_id, orjson.loads(msg))


class OkxPartition(StatefulSourcePartition):
    def __init__(self, inst_id: str):
        gen = _ws_gen(inst_id)
        self._batch = batch_async(gen, timeout=timedelta(seconds=0.1), batch_size=10)

    def next_batch(self):
        return next(self._batch)

    def snapshot(self):
        return None


@dataclass
class OkxSource(FixedPartitionedSource):
    inst_ids: List[str]

    def list_parts(self):
        return self.inst_ids

    def build_part(self, step_id, for_key, _resume_state):
        return OkxPartition(for_key)


@dataclass
class OrderBookState:
    data: Dict = None

    def update(self, data):
        self.data = data

    def summary(self):
        return self.data


flow = Dataflow("orderbook")

# test with 100 inst_ids, generate 100 inst_ids for me
inst_ids = ["BTC-USDT", "ETH-USDT", "LTC-USDT", "XRP-USDT", "DOT-USDT", "ADA-USDT", "BCH-USDT", "LINK-USDT", "XLM-USDT",
            "USDT-USDT", "UNI-USDT", "WBTC-USDT", "AAVE-USDT", "LTC-USDT", "EOS-USDT", "XMR-USDT", "TRX-USDT",]

inp = op.input("input", flow=flow, source=OkxSource(inst_ids=inst_ids))


def mapper(state, value):
    """Update the state with the given value and return the state and a summary."""
    if state is None:
        state = OrderBookState()

    state.update(value)
    return (state, state.summary())


stats = op.stateful_map("orderbook", inp, mapper)
op.output("out", stats, StdOutSink())
#!/usr/bin/env python

