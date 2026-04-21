# web/tests/test_models.py
"""ORM 模型单元测试。"""

import pytest

from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.user import User


def test_create_user(db_session):
    user = User(phone="13800138000", nickname="测试用户")
    db_session.add(user)
    db_session.commit()

    result = db_session.query(User).filter_by(phone="13800138000").one()
    assert result.id is not None
    assert result.phone == "13800138000"
    assert result.nickname == "测试用户"
    assert result.is_active is True
    assert result.is_admin is False
    assert result.phone_verified is True
    assert result.avatar_url is None
    assert result.wechat_openid is None


def test_create_credit_account(db_session):
    user = User(phone="13800138001", nickname="积分用户")
    db_session.add(user)
    db_session.commit()

    account = CreditAccount(user_id=user.id)
    db_session.add(account)
    db_session.commit()

    result = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert result.balance == 0
    assert result.total_recharged == 0
    assert result.total_consumed == 0


def test_user_credit_account_relationship(db_session):
    user = User(phone="13800138002", nickname="关系用户")
    db_session.add(user)
    db_session.commit()

    account = CreditAccount(user_id=user.id, balance=100)
    db_session.add(account)
    db_session.commit()

    db_session.refresh(user)
    assert user.credit_account.balance == 100


def test_user_phone_unique(db_session):
    user1 = User(phone="13800138003", nickname="用户A")
    db_session.add(user1)
    db_session.commit()

    user2 = User(phone="13800138003", nickname="用户B")
    db_session.add(user2)
    with pytest.raises(Exception):
        db_session.commit()
