# web/src/aigc_web/schemas/credits.py
"""积分相关的请求/响应模型。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


# --- 套餐 ---

class PackageResponse(BaseModel):
    id: int
    name: str
    price_cents: int
    credits: int
    bonus_credits: int

    model_config = {"from_attributes": True}


# --- 充值 ---

class RechargeRequest(BaseModel):
    package_id: int
    pay_method: Literal["pc_web", "h5"]


class RechargeResponse(BaseModel):
    order_id: int
    pay_url: str


# --- 订单 ---

class OrderResponse(BaseModel):
    id: int
    out_trade_no: str
    amount_cents: int
    credits_granted: int
    status: str
    pay_method: str
    created_at: datetime
    paid_at: datetime | None


# --- 流水 ---

class TransactionResponse(BaseModel):
    id: int
    trade_no: str
    type: str
    amount: int
    balance_after: int
    remark: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    size: int


# --- 余额 ---

class BalanceResponse(BaseModel):
    balance: int
    total_recharged: int
    total_consumed: int
