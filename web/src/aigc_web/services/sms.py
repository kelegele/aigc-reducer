# web/src/aigc_web/services/sms.py
"""验证码生成、存储、发送和校验。"""

import random
from datetime import datetime, timedelta, timezone

from aigc_web.config import settings


class _CodeEntry:
    __slots__ = ("code", "expires_at", "sent_at")

    def __init__(self, code: str, expires_at: datetime, sent_at: datetime):
        self.code = code
        self.expires_at = expires_at
        self.sent_at = sent_at


class VerificationCodeService:
    """验证码服务。内存存储，开发模式打印到控制台。"""

    CODE_LENGTH = 6
    CODE_TTL = timedelta(minutes=5)
    SEND_COOLDOWN = timedelta(seconds=60)

    def __init__(self) -> None:
        self._store: dict[str, _CodeEntry] = {}

    def send(self, phone: str) -> None:
        """生成验证码并发送到手机号。60 秒内不可重发。"""
        now = datetime.now(timezone.utc)
        existing = self._store.get(phone)
        if existing and now - existing.sent_at < self.SEND_COOLDOWN:
            remaining = 60 - int((now - existing.sent_at).total_seconds())
            raise ValueError(f"请 {remaining} 秒后再试")

        code = self._generate_code()
        self._store[phone] = _CodeEntry(
            code=code,
            expires_at=now + self.CODE_TTL,
            sent_at=now,
        )
        self._do_send(phone, code)

    def verify(self, phone: str, code: str) -> bool:
        """校验验证码。成功后清除，防止重复使用。"""
        entry = self._store.get(phone)
        if entry is None:
            return False

        now = datetime.now(timezone.utc)
        if now > entry.expires_at:
            del self._store[phone]
            return False

        if entry.code != code:
            return False

        del self._store[phone]
        return True

    def _generate_code(self) -> str:
        return "".join(random.choices("0123456789", k=self.CODE_LENGTH))

    def _do_send(self, phone: str, code: str) -> None:
        if settings.SMS_PROVIDER == "dev":
            print(f"[DEV SMS] 验证码 {code} -> {phone}")
            return
        # 生产环境：调用短信服务商 API（P2 实现）
        print(f"[SMS] 发送验证码到 {phone}（provider={settings.SMS_PROVIDER}）")
