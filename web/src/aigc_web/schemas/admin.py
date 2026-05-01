# web/src/aigc_web/schemas/admin.py
"""管理后台请求/响应模型。"""

from datetime import datetime

from pydantic import BaseModel


# --- 套餐管理 ---

class PackageCreateRequest(BaseModel):
    name: str
    price_cents: int
    credits: int
    bonus_credits: int = 0
    sort_order: int = 0
    is_active: bool = True


class PackageUpdateRequest(BaseModel):
    name: str | None = None
    price_cents: int | None = None
    credits: int | None = None
    bonus_credits: int | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class AdminPackageResponse(BaseModel):
    id: int
    name: str
    price_cents: int
    credits: int
    bonus_credits: int
    sort_order: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- 用户管理 ---

class AdminUserResponse(BaseModel):
    id: int
    phone: str
    nickname: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    credit_balance: int
    total_recharged: int
    total_consumed: int
    total_recharge_cents: int = 0


class UserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    size: int


class AdjustCreditsRequest(BaseModel):
    amount: int
    remark: str = "管理员调整"


class SetUserStatusRequest(BaseModel):
    is_active: bool


# --- 看板 ---

class TopUserEntry(BaseModel):
    user_id: int
    nickname: str
    phone: str
    amount: int


class DashboardResponse(BaseModel):
    total_users: int
    total_revenue_cents: int
    total_credits_granted: int
    total_credits_consumed: int
    today_new_users: int
    total_detections: int
    today_detections: int
    top_recharge_users: list[TopUserEntry]
    top_consume_users: list[TopUserEntry]


# --- 配置 ---

class ConfigResponse(BaseModel):
    credits_per_1k_tokens: float
    new_user_bonus_credits: int


class ConfigUpdateRequest(BaseModel):
    credits_per_1k_tokens: float | None = None
    new_user_bonus_credits: int | None = None


# --- 流水管理 ---

class AdminTransactionResponse(BaseModel):
    id: int
    trade_no: str
    user_id: int
    user_phone: str
    user_nickname: str
    type: str
    amount: int
    balance_after: int
    ref_type: str | None
    ref_id: str | int | None
    remark: str | None
    created_at: datetime


class AdminTransactionListResponse(BaseModel):
    items: list[AdminTransactionResponse]
    total: int
    page: int
    size: int


# --- 内容管理（检测记录） ---

class AdminTaskResponse(BaseModel):
    id: str
    user_id: int
    user_phone: str
    user_nickname: str
    title: str
    status: str
    detect_mode: str
    style: str
    full_reconstruct: bool
    total_credits: int
    paragraph_count: int
    created_at: datetime
    completed_at: datetime | None = None


class AdminTaskListResponse(BaseModel):
    items: list[AdminTaskResponse]
    total: int
    page: int
    size: int
