"""
这个简化版本包含了以下核心功能：
仓位管理:
    支持HEDGING和NETTING两种模式
    仓位创建、更新和平仓
    计算未实现和已实现盈亏
投资组合管理:
    维护仓位索引（按策略、按品种）
    计算总体盈亏
    查询仓位功能
数据模型:
    Position: 仓位信息
    Portfolio: 投资组合
    PositionManager: 仓位管理器
核心业务逻辑:
    NETTING模式下合并同策略同品种的仓位
    HEDGING模式下为每笔交易创建独立仓位
    维护仓位状态和盈亏计算
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4


# 枚举定义
class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class OmsType(Enum):
    HEDGING = "HEDGING"
    NETTING = "NETTING"


# 数据模型
@dataclass
class Position:
    id: str
    instrument_id: str
    strategy_id: str
    side: PositionSide
    quantity: Decimal
    entry_price: Decimal
    unrealized_pnl: Decimal = Decimal(0)
    realized_pnl: Decimal = Decimal(0)

    @property
    def is_open(self) -> bool:
        return self.quantity != 0

    def update(self, fill_qty: Decimal, fill_price: Decimal):
        self.quantity += fill_qty
        # 更新平均持仓价格
        if self.quantity > 0:
            self.entry_price = (
                self.entry_price * self.quantity + fill_price * fill_qty
            ) / self.quantity

    def calculate_unrealized_pnl(self, current_price: Decimal) -> Decimal:
        if self.side == PositionSide.LONG:
            return (current_price - self.entry_price) * self.quantity
        elif self.side == PositionSide.SHORT:
            return (self.entry_price - current_price) * self.quantity
        return Decimal(0)


class Portfolio:
    def __init__(self):
        self.positions: Dict[str, Position] = {}  # position_id -> Position
        self.strategy_positions: Dict[
            str, List[str]
        ] = {}  # strategy_id -> [position_id]
        self.instrument_positions: Dict[
            str, List[str]
        ] = {}  # instrument_id -> [position_id]

    def add_position(self, position: Position):
        self.positions[position.id] = position

        # 更新索引
        if position.strategy_id not in self.strategy_positions:
            self.strategy_positions[position.strategy_id] = []
        self.strategy_positions[position.strategy_id].append(position.id)

        if position.instrument_id not in self.instrument_positions:
            self.instrument_positions[position.instrument_id] = []
        self.instrument_positions[position.instrument_id].append(position.id)

    def get_strategy_positions(self, strategy_id: str) -> List[Position]:
        position_ids = self.strategy_positions.get(strategy_id, [])
        return [self.positions[pid] for pid in position_ids]

    def get_instrument_positions(self, instrument_id: str) -> List[Position]:
        position_ids = self.instrument_positions.get(instrument_id, [])
        return [self.positions[pid] for pid in position_ids]

    def calculate_total_pnl(self) -> Decimal:
        return sum(p.unrealized_pnl + p.realized_pnl for p in self.positions.values())


class PositionManager:
    def __init__(self, oms_type: OmsType):
        self.oms_type = oms_type
        self.portfolio = Portfolio()

    def handle_fill(
        self,
        strategy_id: str,
        instrument_id: str,
        order_side: OrderSide,
        quantity: Decimal,
        price: Decimal,
    ) -> Position:
        """处理订单成交"""

        if self.oms_type == OmsType.NETTING:
            position_id = f"{instrument_id}-{strategy_id}"
            position = self.portfolio.positions.get(position_id)

            if position is None:
                # 创建新仓位
                position = Position(
                    id=position_id,
                    instrument_id=instrument_id,
                    strategy_id=strategy_id,
                    side=PositionSide.LONG
                    if order_side == OrderSide.BUY
                    else PositionSide.SHORT,
                    quantity=Decimal(0),
                    entry_price=price,
                )
                self.portfolio.add_position(position)

            # 更新仓位
            fill_qty = quantity if order_side == OrderSide.BUY else -quantity
            position.update(fill_qty, price)

        else:  # HEDGING
            # 每笔交易创建新仓位
            position_id = f"{instrument_id}-{strategy_id}-{uuid4()}"
            position = Position(
                id=position_id,
                instrument_id=instrument_id,
                strategy_id=strategy_id,
                side=PositionSide.LONG
                if order_side == OrderSide.BUY
                else PositionSide.SHORT,
                quantity=quantity,
                entry_price=price,
            )
            self.portfolio.add_position(position)

        return position

    def close_position(self, position_id: str, price: Decimal):
        """平仓"""
        position = self.portfolio.positions.get(position_id)
        if position and position.is_open:
            # 计算已实现盈亏
            position.realized_pnl = position.calculate_unrealized_pnl(price)
            position.quantity = Decimal(0)
            position.unrealized_pnl = Decimal(0)


# 使用示例
def example_usage():
    # 创建NETTING模式的仓位管理器
    manager = PositionManager(OmsType.NETTING)

    # 处理买入订单成交
    position = manager.handle_fill(
        strategy_id="strategy-1",
        instrument_id="BTC-USDT",
        order_side=OrderSide.BUY,
        quantity=Decimal("1.0"),
        price=Decimal("50000"),
    )

    # 更新未实现盈亏
    current_price = Decimal("51000")
    position.unrealized_pnl = position.calculate_unrealized_pnl(current_price)

    # 获取策略的所有仓位
    strategy_positions = manager.portfolio.get_strategy_positions("strategy-1")

    # 平仓
    manager.close_position(position.id, Decimal("51000"))

    # 计算总盈亏
    total_pnl = manager.portfolio.calculate_total_pnl()
    print(f"Total PnL: {total_pnl}")


if __name__ == "__main__":
    example_usage()
