# web/tests/test_sms.py
"""验证码服务测试。"""

import pytest

from aigc_web.services.sms import VerificationCodeService


@pytest.fixture
def sms_service():
    return VerificationCodeService()


def test_send_creates_code(sms_service):
    sms_service.send("13800138000")
    # 验证码已存储，可通过 verify 校验


def test_verify_correct_code(sms_service):
    sms_service.send("13800138000")
    # 从 _store 中取出验证码（仅测试用）
    code = sms_service._store["13800138000"].code
    assert sms_service.verify("13800138000", code) is True


def test_verify_wrong_code(sms_service):
    sms_service.send("13800138000")
    assert sms_service.verify("13800138000", "000000") is False


def test_verify_expired_code(sms_service):
    sms_service.send("13800138000")
    code = sms_service._store["13800138000"].code
    # 模拟过期
    from datetime import datetime, timedelta, timezone
    sms_service._store["13800138000"].expires_at = datetime.now(timezone.utc) - timedelta(
        seconds=1
    )
    assert sms_service.verify("13800138000", code) is False


def test_verify_code_consumed_on_success(sms_service):
    sms_service.send("13800138000")
    code = sms_service._store["13800138000"].code
    assert sms_service.verify("13800138000", code) is True
    # 二次使用应失败
    assert sms_service.verify("13800138000", code) is False


def test_verify_nonexistent_phone(sms_service):
    assert sms_service.verify("13800138000", "123456") is False


def test_send_cooldown(sms_service):
    sms_service.send("13800138000")
    with pytest.raises(ValueError, match="秒后再试"):
        sms_service.send("13800138000")
