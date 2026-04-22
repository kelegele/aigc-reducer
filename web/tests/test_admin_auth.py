# web/tests/test_admin_auth.py
"""管理员权限和开发环境验证码跳过测试。"""

import pytest
from aigc_web.models.user import User
from aigc_web.services import sms as sms_service


def test_require_admin_non_admin(db_session):
    """非管理员调用 require_admin 应抛 403。"""
    from fastapi import HTTPException
    from aigc_web.dependencies import require_admin
    from aigc_web.services.token import create_access_token

    user = User(phone="13800138000", nickname="普通用户", is_admin=False)
    db_session.add(user)
    db_session.commit()
    token = create_access_token(user.id)

    import asyncio
    with pytest.raises(HTTPException) as exc_info:
        asyncio.get_event_loop().run_until_complete(require_admin(token=token, db=db_session))
    assert exc_info.value.status_code == 403


def test_require_admin_is_admin(db_session):
    """管理员调用 require_admin 应返回 User。"""
    from aigc_web.dependencies import require_admin
    from aigc_web.services.token import create_access_token

    user = User(phone="13800138001", nickname="管理员", is_admin=True)
    db_session.add(user)
    db_session.commit()
    token = create_access_token(user.id)

    import asyncio
    result = asyncio.get_event_loop().run_until_complete(require_admin(token=token, db=db_session))
    assert result.id == user.id
    assert result.is_admin is True


def test_dev_bypass_all_phones(db_session, monkeypatch):
    """DEV_BYPASS_PHONE=True 时所有手机号跳过验证码。"""
    from aigc_web import config
    monkeypatch.setattr(config.settings, "DEV_BYPASS_PHONE", True)
    monkeypatch.setattr(config.settings, "SMS_PROVIDER", "dev")

    svc = sms_service.VerificationCodeService()
    assert svc.verify("13800138000", "000000") is True
    assert svc.verify("13999999999", "123456") is True


def test_dev_bypass_test_phones_only(db_session, monkeypatch):
    """DEV_TEST_PHONES 配置时仅指定手机号跳过。"""
    from aigc_web import config
    monkeypatch.setattr(config.settings, "DEV_TEST_PHONES", "13800138000,13800138001")
    monkeypatch.setattr(config.settings, "DEV_BYPASS_PHONE", False)
    monkeypatch.setattr(config.settings, "SMS_PROVIDER", "dev")

    svc = sms_service.VerificationCodeService()
    assert svc.verify("13800138000", "000000") is True
    assert svc.verify("13800138001", "123456") is True
    assert svc.verify("13999999999", "000000") is False


def test_dev_bypass_not_dev_provider(db_session, monkeypatch):
    """非 dev 模式下不跳过验证码。"""
    from aigc_web import config
    monkeypatch.setattr(config.settings, "DEV_BYPASS_PHONE", True)
    monkeypatch.setattr(config.settings, "SMS_PROVIDER", "aliyun")

    svc = sms_service.VerificationCodeService()
    assert svc.verify("13800138000", "000000") is False
