from enum import Enum
from typing import Dict, List, Optional

# 定义订单状态
class OrderState(Enum):
    """订单状态枚举类"""
    CREATED = "created"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class OrderStateMachine:
    """订单状态机

    负责管理订单在不同状态之间的转换
    """

    def __init__(self) -> None:
        # 初始化状态转换规则
        self.state_transitions: Dict[OrderState, List[OrderState]] = {
            OrderState.CREATED: [OrderState.PAID, OrderState.CANCELLED],
            OrderState.PAID: [OrderState.SHIPPED, OrderState.CANCELLED],
            OrderState.SHIPPED: [OrderState.DELIVERED],
            OrderState.DELIVERED: [],
            OrderState.CANCELLED: []
        }
        self.current_state: OrderState = OrderState.CREATED

    def can_transition_to(self, new_state: OrderState) -> bool:
        """检查是否可以转换到目标状态"""
        return new_state in self.state_transitions[self.current_state]

    def transition_to(self, new_state: OrderState) -> bool:
        if self.can_transition_to(new_state):
            self.current_state = new_state
            print(f"订单状态从 {self.current_state.value} 转换到 {new_state.value}")
            return True
        else:
            print(f"无法从 {self.current_state.value} 转换到 {new_state.value}")
            return False

# 使用示例
order = OrderStateMachine()
order.transition_to(OrderState.PAID)      # 成功：created -> paid
order.transition_to(OrderState.SHIPPED)   # 成功：paid -> shipped
order.transition_to(OrderState.CREATED)   # 失败：shipped -> created（非法转换）
order.transition_to(OrderState.DELIVERED) # 成功：shipped -> delivered
