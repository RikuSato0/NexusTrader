---
myst:
  enable_extensions:
    - html_image
---

| Framework                                                                                                       | Websocket Package                                                                   | Data Serialization                                 | Strategy Support |
|-----------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|----------------------------------------------------|------------------|
| TradeBot                                                                                                    | [picows](https://picows.readthedocs.io/en/stable/introduction.html#installation)    | [msgspec](https://jcristharif.com/msgspec/)        | ✅                |
| [HummingBot](https://github.com/hummingbot/hummingbot?tab=readme-ov-file)                                       | aiohttp                                                                             | [ujson](https://pypi.org/project/ujson/)           | ✅                |
| [Freqtrade](https://github.com/freqtrade/freqtrade)                                                             | websockets                                                                          | [orjson](https://github.com/ijl/orjson)            | ✅                |
| [crypto-feed](https://github.com/bmoscon/cryptofeed)                                                            | [websockets](https://websockets.readthedocs.io/en/stable/)                          | [yapic.json](https://pypi.org/project/yapic.json/) | ❌                |
| [ccxt](https://github.com/bmoscon/cryptofeed)                                                                   | [aiohttp](https://docs.aiohttp.org/en/stable/client_reference.html)                 | json                                               | ❌                |
| [binance-futures-connector](https://github.com/binance/binance-futures-connector-python)                        | [websocket-client](https://websocket-client.readthedocs.io/en/latest/examples.html) | json                                               | ❌                |
| [python-okx](https://github.com/okxapi/python-okx)                                                              | websockets                                                                          | json                                               | ❌                |
| [unicorn-binance-websocket-api](https://github.com/LUCIT-Systems-and-Development/unicorn-binance-websocket-api) | websockets                                                                          | [ujson](https://pypi.org/project/ujson/)           | ❌                |
