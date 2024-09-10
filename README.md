# 简介

## Docker
1. copy the `Dockerfile` in the work dir.
```
docker build -t tradebot .
docker run -itd --name bot tradebot /bin/bash
```

2. `crtl+D` exit the docker.

3. re-enter the docker container
```
docker exec -it bot /bin/bash
```




## manager.py:

- NatsManager 负责触发事件驱动
    - 订阅`bookTicker`以推送数据
- ExchangeManager 负责对接`ccxt` 
- OrderManager 负责下单，组合ExchangeManager
- AccountManager 负责处理`position`和`balance`

## entity.py

- EventSystem 负责订阅各种事件，包括ratio,order update,position update等事件
- OrderResponse 封装的order返回
- Quote `quote`数据结构，储存`ask`和`bid`
- MarketDataStore 储存推送数据，可通过`MarketDataStore.quote[symbol]`获得一个`quote`对象
- Account 负责储存balance，主要是`USDT`,`BNB`等`base asset`
- Position 负责记录`symbol`持仓
- PositionDict 负责储存整个`bot`的持仓
- Context 全局变量，包含`spot_account`, `futures_account`, `position`等三个属性

## bot.py

- TradingBot: 基类
- Bot: 继承自`TradingBot`

## main.py
- main 主函数

# Manager.py 文档

## NatsManager 类

负责处理 NATS 连接和订阅。

### 方法：
- `__init__(self, nats_url, cert_path)`: 初始化 NATS 管理器。
- `_connect()`: 建立 NATS 连接。
- `subscribe()`: 订阅特定主题并开始处理消息。
- `_callback(msg)`: 处理接收到的消息。
- `_process_queue()`: 处理消息队列。

## ExchangeManager 类

管理与交易所的连接和交互。

### 方法：
- `__init__(self, config)`: 初始化交易所管理器。
- `_init_exchange()`: 初始化交易所 API。
- `load_markets()`: 加载市场数据。
- `close()`: 关闭连接。
- `watch_user_data_stream()`: 监控用户数据流。
- `_process_queue()`: 处理消息队列。

## AccountManager 类

管理账户信息更新。

### 方法：
- `__init__()`: 初始化账户管理器。
- `_on_account_update(res, typ)`: 处理账户更新事件。
- `_on_position_update(order)`: 处理持仓更新事件。

## OrderManager 类

管理订单操作和更新。

### 方法：
- `__init__(self, exchange)`: 初始化订单管理器。
- `_on_order_update(res, typ)`: 处理订单更新事件。
- `place_limit_order(symbol, side, amount, price, close_position, client_order_id)`: 下限价单。
- `place_market_order(symbol, side, amount, close_position, client_order_id)`: 下市价单。
- `cancel_order(order_id, symbol)`: 取消订单。

## 主要功能：

1. NATS 消息处理：通过 NatsManager 处理 NATS 连接和消息订阅。
2. 交易所交互：使用 ExchangeManager 与交易所 API 进行交互。
3. 账户管理：AccountManager 处理账户和持仓更新。
4. 订单管理：OrderManager 处理订单的创建、更新和取消。

# Entity 文档

## OrderResponse 类

表示订单响应的数据类。

### 属性：
- id: str
- symbol: str
- status: str
- side: Literal['buy', 'sell']
- amount: float
- filled: float
- last_filled: float
- client_order_id: str
- average: float
- price: float

### 方法：
- `__getitem__`, `__setitem__`, `keys`, `__iter__`, `__len__`: 实现类字典接口。

## Quote 类

表示报价的类。

### 属性：
- ask: float
- bid: float

### 方法：
- `__getitem__`, `__setitem__`, `__repr__`: 实现类字典接口和字符串表示。

## MarketDataStore 类

管理市场数据的静态类。

### 类属性：
- quote: Dict[str, Quote]
- open_ratio: Dict
- close_ratio: Dict

### 类方法：
- `update(data: Dict)`: 更新报价数据。
- `calculate_ratio(spot_symbol: str)`: 计算开仓和平仓比率。

## EventSystem 类

实现事件系统的静态类。

### 类方法：
- `on(event: str, callback: Callable)`: 注册事件监听器。
- `emit(event: str, *args: Any, **kwargs: Any)`: 触发事件。

## Account 类

表示账户的数据类。

### 属性：
- USDT, BNB, FDUSD, BTC, ETH, USDC: float

### 方法：
- `save_account()`: 保存账户数据到文件。
- `load_account()`: 从文件加载账户数据。

## Position 类

表示持仓的数据类。

### 属性：
- symbol: str
- amount: float
- last_price: float
- avg_price: float
- total_cost: float

### 方法：
- `update(order_amount, order_price)`: 更新持仓信息。

## PositionDict 类

管理多个持仓的字典类。

### 方法：
- `update(symbol: str, order_amount: float, order_price: float)`: 更新特定持仓。
- `load_positions()`: 从文件加载持仓数据。
- `save_positions()`: 保存持仓数据到文件。

## Context 类

表示整体上下文的类。

### 属性：
- spot_account: Account
- futures_account: Account
- position: PositionDict

## 主要功能：

1. 订单响应处理：使用 OrderResponse 类表示订单响应。
2. 市场数据管理：通过 MarketDataStore 类管理报价和比率数据。
3. 事件系统：使用 EventSystem 类实现事件的注册和触发。
4. 账户管理：Account 类处理不同类型的账户余额。
5. 持仓管理：Position 和 PositionDict 类管理持仓信息。
6. 上下文管理：Context 类整合了账户和持仓信息。

