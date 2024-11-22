from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
import uuid


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


# 数据类定义
@dataclass
class OrderFilled:
    instrument_id: str
    order_side: OrderSide
    quantity: Decimal
    price: Decimal
    position_id: str
    strategy_id: str
    commission: Decimal


@dataclass
class Position:
    id: str
    instrument_id: str
    strategy_id: str
    side: PositionSide
    quantity: Decimal
    entry_price: Decimal
    realized_pnl: Decimal = Decimal(0)
    unrealized_pnl: Decimal = Decimal(0)

    @property
    def is_closed(self) -> bool:
        """判断仓位是否已平"""
        return self.quantity == Decimal(0)

    def calculate_pnl(self, current_price: Decimal) -> None:
        """计算未实现盈亏"""
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        elif self.side == PositionSide.SHORT:
            self.unrealized_pnl = (self.entry_price - current_price) * self.quantity

    def close(self, price: Decimal) -> Decimal:
        """平仓并返回实现盈亏"""
        if self.side == PositionSide.LONG:
            pnl = (price - self.entry_price) * self.quantity
        else:
            pnl = (self.entry_price - price) * self.quantity

        self.realized_pnl += pnl
        self.quantity = Decimal(0)
        self.side = PositionSide.FLAT
        return pnl

    @classmethod
    def from_fill(cls, fill: OrderFilled) -> "Position":
        return cls(
            id=fill.position_id,
            instrument_id=fill.instrument_id,
            strategy_id=fill.strategy_id,
            side=PositionSide.LONG
            if fill.order_side == OrderSide.BUY
            else PositionSide.SHORT,
            quantity=fill.quantity,
            entry_price=fill.price,
        )

    def update(self, fill: OrderFilled) -> None:
        """更新仓位"""
        if fill.order_side == OrderSide.BUY:
            self._handle_buy(fill)
        else:
            self._handle_sell(fill)

    def _handle_buy(self, fill: OrderFilled) -> None:
        if self.side == PositionSide.LONG:
            # 多仓加仓
            new_quantity = self.quantity + fill.quantity
            self.entry_price = (
                self.entry_price * self.quantity + fill.price * fill.quantity
            ) / new_quantity
            self.quantity = new_quantity
        elif self.side == PositionSide.SHORT:
            # 空仓减仓
            if fill.quantity > self.quantity:
                # 仓位反转
                remaining = fill.quantity - self.quantity
                self.realized_pnl += (self.entry_price - fill.price) * self.quantity
                self.side = PositionSide.LONG
                self.quantity = remaining
                self.entry_price = fill.price
            else:
                # 部分平仓
                self.quantity -= fill.quantity
                self.realized_pnl += (self.entry_price - fill.price) * fill.quantity

    def _handle_sell(self, fill: OrderFilled) -> None:
        if self.side == PositionSide.SHORT:
            # 空仓加仓
            new_quantity = self.quantity + fill.quantity
            self.entry_price = (
                self.entry_price * self.quantity + fill.price * fill.quantity
            ) / new_quantity
            self.quantity = new_quantity
        elif self.side == PositionSide.LONG:
            # 多仓减仓
            if fill.quantity > self.quantity:
                # 仓位反转
                remaining = fill.quantity - self.quantity
                self.realized_pnl += (fill.price - self.entry_price) * self.quantity
                self.side = PositionSide.SHORT
                self.quantity = remaining
                self.entry_price = fill.price
            else:
                # 部分平仓
                self.quantity -= fill.quantity
                self.realized_pnl += (fill.price - self.entry_price) * fill.quantity


class Portfolio:
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.strategy_positions: Dict[str, List[str]] = {}
        self.instrument_positions: Dict[str, List[str]] = {}

    def get_position(self, instrument_id: str, strategy_id: str) -> Optional[Position]:
        """获取NETTING模式下的仓位"""
        position_id = f"{instrument_id}-{strategy_id}"
        return self.positions.get(position_id)

    def get_open_positions(
        self,
        strategy_id: Optional[str] = None,
        instrument_id: Optional[str] = None,
        side: Optional[PositionSide] = None,
    ) -> List[Position]:
        """获取未平仓位"""
        positions = []
        for pos_id in self.open_positions:
            pos = self.positions[pos_id]
            if strategy_id and pos.strategy_id != strategy_id:
                continue
            if instrument_id and pos.instrument_id != instrument_id:
                continue
            if side and pos.side != side:
                continue
            positions.append(pos)
        return positions

    def handle_fill(self, fill: OrderFilled, oms_type: OmsType) -> None:
        """处理成交"""
        if oms_type == OmsType.NETTING:
            position_id = f"{fill.instrument_id}-{fill.strategy_id}"
        else:  # HEDGING
            position_id = str(uuid.uuid4())

        fill.position_id = position_id
        position = self.positions.get(position_id)

        if position is None:
            # 新建仓位
            position = Position.from_fill(fill)
            self.positions[position_id] = position
            self.strategy_positions.setdefault(fill.strategy_id, []).append(position_id)
            self.instrument_positions.setdefault(fill.instrument_id, []).append(
                position_id
            )
        else:
            # 更新现有仓位
            position.update(fill)

            # 如果仓位已平，从活动仓位列表中移除
            if position.is_closed:
                if position_id in self.strategy_positions.get(fill.strategy_id, []):
                    self.strategy_positions[fill.strategy_id].remove(position_id)
                if position_id in self.instrument_positions.get(fill.instrument_id, []):
                    self.instrument_positions[fill.instrument_id].remove(position_id)

    def get_strategy_positions(self, strategy_id: str) -> List[Position]:
        """获取策略的所有仓位"""
        position_ids = self.strategy_positions.get(strategy_id, [])
        return [self.positions[pid] for pid in position_ids]

    def get_instrument_positions(self, instrument_id: str) -> List[Position]:
        """获取品种的所有仓位"""
        position_ids = self.instrument_positions.get(instrument_id, [])
        return [self.positions[pid] for pid in position_ids]

    def calculate_net_position(self, instrument_id: str) -> Decimal:
        """计算品种的净仓位"""
        positions = self.get_instrument_positions(instrument_id)
        net = Decimal(0)
        for pos in positions:
            if pos.side == PositionSide.LONG:
                net += pos.quantity
            elif pos.side == PositionSide.SHORT:
                net -= pos.quantity
        return net

    # def _handle_hedging_open(self, fill: OrderFilled) -> str:
    #     """处理HEDGING模式开仓"""
    #     position_id = str(uuid.uuid4())
    #     position = Position(
    #         id=position_id,
    #         instrument_id=fill.instrument_id,
    #         strategy_id=fill.strategy_id,
    #         side=PositionSide.LONG if fill.order_side == OrderSide.BUY else PositionSide.SHORT,
    #         quantity=fill.quantity,
    #         entry_price=fill.price,
    #         entry_order_id=fill.order_id,
    #         entry_time=fill.timestamp,
    #     )

    #     # 保存仓位
    #     self.positions[position_id] = position
    #     self.open_positions.add(position_id)

    #     # 更新索引
    #     self.strategy_positions.setdefault(fill.strategy_id, set()).add(position_id)
    #     self.instrument_positions.setdefault(fill.instrument_id, set()).add(position_id)

    #     return position_id

    def _handle_hedging_close(self, fill: OrderFilled) -> None:
        """处理HEDGING模式平仓"""
        position = self.positions.get(fill.close_position_id)
        if not position:
            raise ValueError(f"Position not found: {fill.close_position_id}")

        if position.is_closed:
            raise ValueError(f"Position already closed: {fill.close_position_id}")

        # 检查平仓方向是否正确
        if (
            position.side == PositionSide.LONG and fill.order_side != OrderSide.SELL
        ) or (position.side == PositionSide.SHORT and fill.order_side != OrderSide.BUY):
            raise ValueError(
                f"Invalid close order side for position {fill.close_position_id}"
            )

        # 检查平仓数量是否匹配
        if fill.quantity != position.quantity:
            raise ValueError(
                f"Close quantity mismatch for position {fill.close_position_id}"
            )

        # 平仓
        position.close(fill)
        self.open_positions.remove(position.id)


# 使用示例
def example_usage():
    portfolio = Portfolio()

    # NETTING模式示例
    fill1 = OrderFilled(
        instrument_id="BTC-USDT",
        order_side=OrderSide.BUY,
        quantity=Decimal("1.0"),
        price=Decimal("50000"),
        position_id="",  # 将由系统分配
        strategy_id="Strategy-1",
        commission=Decimal("5"),
    )

    portfolio.handle_fill(fill1, OmsType.NETTING)

    # HEDGING模式示例
    fill2 = OrderFilled(
        instrument_id="BTC-USDT",
        order_side=OrderSide.BUY,
        quantity=Decimal("0.5"),
        price=Decimal("51000"),
        position_id="",  # 将由系统分配
        strategy_id="Strategy-1",
        commission=Decimal("2.5"),
    )

    portfolio.handle_fill(fill2, OmsType.HEDGING)

    # 查询仓位
    strategy_positions = portfolio.get_strategy_positions("Strategy-1")
    net_position = portfolio.calculate_net_position("BTC-USDT")

    return portfolio, strategy_positions, net_position
