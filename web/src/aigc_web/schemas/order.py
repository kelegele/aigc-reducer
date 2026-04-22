# web/src/aigc_web/schemas/order.py
"""订单相关请求/响应模型。"""

from datetime import datetime

from pydantic import BaseModel


class OrderListItem(BaseModel):
    id: int
    out_trade_no: str
    amount_cents: int
    credits_granted: int
    status: str
    pay_method: str
    created_at: datetime
    paid_at: datetime | None


class OrderDetail(OrderListItem):
    credit_transaction_id: int | None
    package_name: str


class AdminOrderDetail(OrderDetail):
    user_id: int
    user_phone: str
    user_nickname: str


class OrderListResponse(BaseModel):
    items: list[OrderListItem]
    total: int
    page: int
    size: int


class AdminOrderListResponse(BaseModel):
    items: list[AdminOrderDetail]
    total: int
    page: int
    size: int
