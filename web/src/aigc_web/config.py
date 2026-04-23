"""应用配置 — 从环境变量 / .env 文件读取。"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "sqlite:///./dev.db"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 短信服务（"dev" = 开发模式，验证码打印到控制台）
    SMS_PROVIDER: str = "dev"
    SMS_ACCESS_KEY: str = ""
    SMS_ACCESS_SECRET: str = ""
    SMS_SIGN_NAME: str = ""
    SMS_TEMPLATE_CODE: str = ""

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # 站点 URL（用于拼接支付回跳、回调地址等）
    SITE_URL: str = "http://localhost:5173"

    # 积分配置
    NEW_USER_BONUS_CREDITS: int = 0
    CREDITS_PER_TOKEN: float = 1.0  # 每 1000 Token 消耗积分数

    # 支付宝配置
    ALIPAY_APP_ID: str = ""
    ALIPAY_PRIVATE_KEY: str = ""
    ALIPAY_PUBLIC_KEY: str = ""

    # 订单超时
    ORDER_TIMEOUT_MINUTES: int = 15  # pending 订单超时时间（分钟）

    # 开发环境测试账号
    DEV_TEST_PHONES: str = ""
    DEV_BYPASS_PHONE: bool = False

    # 超管手机号；登录时自动提升 is_admin
    ADMIN_PHONE: str = ""

    # ── 基于 SITE_URL 的计算属性 ──

    @property
    def alipay_debug(self) -> bool:
        """自动推断：localhost = 沙箱，否则 = 正式。"""
        return "localhost" in self.SITE_URL

    def get_return_url(self, order_id: int) -> str:
        """支付宝同步跳转地址（用户浏览器回跳到前端）。"""
        return f"{self.SITE_URL}/credits?order_id={order_id}"

    def get_notify_url(self) -> str:
        """支付宝异步回调地址（支付宝服务器调用后端）。"""
        return f"{self.SITE_URL}/api/credits/payment/callback"

    model_config = {"env_file": str(Path(__file__).resolve().parents[2] / ".env"), "extra": "ignore"}


settings = Settings()
