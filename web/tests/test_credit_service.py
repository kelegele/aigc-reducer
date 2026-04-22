# web/tests/test_credit_service.py
"""积分服务单元测试。"""

import pytest

from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.credit_transaction import CreditTransaction
from aigc_web.models.user import User
from aigc_web.services import credit as credit_service


def _create_user(db_session, phone="13800138000"):
    user = User(phone=phone, nickname=f"用户{phone[-4:]}")
    db_session.add(user)
    db_session.commit()
    account = CreditAccount(user_id=user.id)
    db_session.add(account)
    db_session.commit()
    return user


def test_recharge(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 100, "payment_order", 1, "充值-基础包")

    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 100
    assert account.total_recharged == 100

    tx = db_session.query(CreditTransaction).one()
    assert tx.type == "recharge"
    assert tx.amount == 100
    assert tx.balance_after == 100
    assert tx.ref_type == "payment_order"
    assert tx.ref_id == 1
    assert tx.remark == "充值-基础包"


def test_recharge_multiple(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 50, "payment_order", 1, "第一次")
    credit_service.recharge(db_session, user.id, 30, "payment_order", 2, "第二次")

    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 80
    assert account.total_recharged == 80

    txs = db_session.query(CreditTransaction).order_by(CreditTransaction.id).all()
    assert len(txs) == 2
    assert txs[0].balance_after == 50
    assert txs[1].balance_after == 80


def test_consume(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 100, "payment_order", 1, "充值")
    # consume 的第二个参数是 token_count，cost = max(1, int(token_count/1000 * CREDITS_PER_TOKEN))
    # 默认 CREDITS_PER_TOKEN=1.0，token_count=30000 → cost=30
    credit_service.consume(db_session, user.id, 30000, "detection_task", 10, "检测扣费")

    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 70
    assert account.total_consumed == 30

    txs = db_session.query(CreditTransaction).order_by(CreditTransaction.id).all()
    assert txs[1].type == "consume"
    assert txs[1].amount == -30
    assert txs[1].balance_after == 70
    assert txs[1].ref_type == "detection_task"
    assert txs[1].ref_id == 10


def test_consume_insufficient_balance(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 50, "payment_order", 1, "充值")

    # token_count=100000 → cost=max(1, int(100000/1000 * 1.0))=100 > balance=50
    with pytest.raises(ValueError, match="积分余额不足"):
        credit_service.consume(db_session, user.id, 100000, "detection_task", 1, "扣费")


def test_get_balance(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 200, "payment_order", 1, "充值")
    assert credit_service.get_balance(db_session, user.id) == 200


def test_get_balance_no_account(db_session):
    assert credit_service.get_balance(db_session, 999) == 0


def test_get_transactions(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 100, "payment_order", 1, "充值")
    credit_service.consume(db_session, user.id, 30, "detection_task", 1, "检测扣费")

    result = credit_service.get_transactions(db_session, user.id, page=1, size=10)
    assert result["total"] == 2
    assert len(result["items"]) == 2
    # 默认时间倒序，最新在前
    assert result["items"][0].type == "consume"


def test_get_transactions_filter_by_type(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 100, "payment_order", 1, "充值")
    credit_service.consume(db_session, user.id, 30, "detection_task", 1, "检测扣费")

    result = credit_service.get_transactions(db_session, user.id, type_filter="recharge", page=1, size=10)
    assert result["total"] == 1
    assert result["items"][0].type == "recharge"


def test_get_transactions_pagination(db_session):
    user = _create_user(db_session)
    for i in range(5):
        credit_service.recharge(db_session, user.id, 10, "payment_order", i, f"充值{i}")

    result = credit_service.get_transactions(db_session, user.id, page=2, size=2)
    assert result["total"] == 5
    assert len(result["items"]) == 2
    assert result["page"] == 2


def test_grant_new_user_bonus(db_session):
    user = _create_user(db_session)
    credit_service.grant_new_user_bonus(db_session, user.id)

    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 0  # 默认 NEW_USER_BONUS_CREDITS=0


def test_grant_new_user_bonus_with_config(db_session, monkeypatch):
    from aigc_web import config
    monkeypatch.setattr(config.settings, "NEW_USER_BONUS_CREDITS", 50)

    user = _create_user(db_session)
    credit_service.grant_new_user_bonus(db_session, user.id)

    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 50
    tx = db_session.query(CreditTransaction).one()
    assert tx.remark == "新人赠送"
