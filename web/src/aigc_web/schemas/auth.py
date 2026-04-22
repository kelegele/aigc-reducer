# web/src/aigc_web/schemas/auth.py
"""认证相关的请求/响应模型。"""

from pydantic import BaseModel, Field


class SendSmsRequest(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$", description="手机号")


class PhoneLoginRequest(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$", description="手机号")
    code: str = Field(pattern=r"^\d{6}$", description="6 位验证码")


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    phone: str
    nickname: str
    avatar_url: str | None
    is_active: bool
    is_admin: bool = False
    credit_balance: int = 0

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserResponse


class MessageResponse(BaseModel):
    message: str
