# web/tests/test_auth_service.py
"""认证业务逻辑测试。"""

import pytest

from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.user import User
from aigc_web.services import auth as auth_service
from aigc_web.services.token import create_access_token, create_refresh_token


def test_login_creates_new_user(db_session):
    result = auth_service.login_or_register(db_session, phone="13800138000")

    assert result.user.phone == "13800138000"
    assert result.user.nickname == "用户8000"
    assert result.user.is_active is True
    assert result.user.credit_balance == 0
    assert result.access_token
    assert result.refresh_token

    # 数据库中应有 1 个用户
    assert db_session.query(User).count() == 1


def test_login_returns_existing_user(db_session):
    user = User(phone="13800138000", nickname="已有用户")
    db_session.add(user)
    db_session.commit()

    result = auth_service.login_or_register(db_session, phone="13800138000")
    assert result.user.nickname == "已有用户"
    assert db_session.query(User).count() == 1


def test_login_creates_credit_account(db_session):
    auth_service.login_or_register(db_session, phone="13800138000")
    user = db_session.query(User).filter_by(phone="13800138000").one()
    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 0


def test_refresh_access_token(db_session):
    from aigc_web.services.token import decode_token

    result = auth_service.login_or_register(db_session, phone="13800138000")
    new_access = auth_service.refresh_access_token(db_session, result.refresh_token)
    # Token must be a valid access token for the same user
    user_id = decode_token(new_access, expected_type="access")
    assert user_id == result.user.id


def test_refresh_with_invalid_token(db_session):
    with pytest.raises(ValueError):
        auth_service.refresh_access_token(db_session, "invalid.token.here")


def test_get_current_user(db_session):
    result = auth_service.login_or_register(db_session, phone="13800138000")
    user = auth_service.get_current_user(db_session, result.access_token)
    assert user.phone == "13800138000"


def test_get_current_user_inactive(db_session):
    user = User(phone="13800138000", nickname="禁用用户", is_active=False)
    db_session.add(user)
    db_session.commit()
    token = create_access_token(user.id)
    with pytest.raises(ValueError, match="已禁用"):
        auth_service.get_current_user(db_session, token)


def test_get_user_response(db_session):
    result = auth_service.login_or_register(db_session, phone="13800138000")
    user = auth_service.get_current_user(db_session, result.access_token)
    resp = auth_service.get_user_response(db_session, user)
    assert resp.credit_balance == 0
    assert resp.phone == "13800138000"
