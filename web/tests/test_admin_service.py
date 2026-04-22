# web/tests/test_admin_service.py
"""管理服务单元测试。"""

from datetime import datetime, timezone

import pytest

from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.credit_transaction import CreditTransaction
from aigc_web.models.payment_order import PaymentOrder
from aigc_web.models.recharge_package import RechargePackage
from aigc_web.models.user import User
from aigc_web.services import admin as admin_service
from aigc_web.services import credit as credit_service
from aigc_web.schemas.admin import PackageCreateRequest, PackageUpdateRequest


def _create_user(db_session, phone="13800138000"):
    user = User(phone=phone, nickname=f"用户{phone[-4:]}")
    db_session.add(user)
    db_session.commit()
    account = CreditAccount(user_id=user.id)
    db_session.add(account)
    db_session.commit()
    return user


# --- 套餐管理 ---

def test_list_packages(db_session):
    for i, name in enumerate(["基础包", "专业包"]):
        pkg = RechargePackage(
            name=name, price_cents=(i + 1) * 1000,
            credits=(i + 1) * 100, sort_order=i, is_active=(i == 0),
        )
        db_session.add(pkg)
    db_session.commit()

    pkgs = admin_service.list_packages(db_session)
    assert len(pkgs) == 2
    assert pkgs[0].name == "基础包"


def test_create_package(db_session):
    data = PackageCreateRequest(name="测试包", price_cents=500, credits=50, bonus_credits=5)
    pkg = admin_service.create_package(db_session, data)
    assert pkg.id > 0
    assert pkg.name == "测试包"
    assert pkg.price_cents == 500


def test_update_package(db_session):
    pkg = RechargePackage(name="旧名", price_cents=1000, credits=100)
    db_session.add(pkg)
    db_session.commit()

    data = PackageUpdateRequest(name="新名", is_active=False)
    updated = admin_service.update_package(db_session, pkg.id, data)
    assert updated.name == "新名"
    assert updated.is_active is False


def test_update_package_partial(db_session):
    pkg = RechargePackage(name="套餐", price_cents=1000, credits=100, bonus_credits=0)
    db_session.add(pkg)
    db_session.commit()

    data = PackageUpdateRequest(bonus_credits=10)
    updated = admin_service.update_package(db_session, pkg.id, data)
    assert updated.bonus_credits == 10
    assert updated.name == "套餐"


def test_delete_package(db_session):
    pkg = RechargePackage(name="删除测试", price_cents=100, credits=10)
    db_session.add(pkg)
    db_session.commit()

    admin_service.delete_package(db_session, pkg.id)
    assert db_session.query(RechargePackage).count() == 0


def test_delete_package_with_orders(db_session):
    user = _create_user(db_session)
    pkg = RechargePackage(name="有订单", price_cents=100, credits=10)
    db_session.add(pkg)
    db_session.commit()

    order = PaymentOrder(
        user_id=user.id, package_id=pkg.id, out_trade_no="PAY_DEL_TEST",
        amount_cents=100, credits_granted=10, status="pending", pay_method="pc_web",
    )
    db_session.add(order)
    db_session.commit()

    with pytest.raises(ValueError, match="存在关联订单"):
        admin_service.delete_package(db_session, pkg.id)


# --- 用户管理 ---

def test_list_users(db_session):
    _create_user(db_session, "13800138001")
    _create_user(db_session, "13800138002")

    result = admin_service.list_users(db_session, page=1, size=10)
    assert result["total"] == 2


def test_list_users_search(db_session):
    _create_user(db_session, "13800138001")
    _create_user(db_session, "13800138002")

    result = admin_service.list_users(db_session, search="13800138001")
    assert result["total"] == 1


def test_adjust_credits_positive(db_session):
    user = _create_user(db_session)
    admin_service.adjust_credits(db_session, user.id, 100, "测试加积分")

    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 100

    tx = db_session.query(CreditTransaction).one()
    assert tx.amount == 100
    assert tx.remark == "测试加积分"


def test_adjust_credits_negative(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 200, remark="初始")

    admin_service.adjust_credits(db_session, user.id, -50, "测试扣积分")

    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 150


def test_adjust_credits_insufficient(db_session):
    user = _create_user(db_session)
    with pytest.raises(ValueError, match="积分余额不足"):
        admin_service.adjust_credits(db_session, user.id, -100, "超额扣")


def test_set_user_status(db_session):
    user = _create_user(db_session)
    assert user.is_active is True

    admin_service.set_user_status(db_session, user.id, False)
    db_session.refresh(user)
    assert user.is_active is False

    admin_service.set_user_status(db_session, user.id, True)
    db_session.refresh(user)
    assert user.is_active is True


# --- 看板 ---

def test_get_dashboard(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 100, remark="充值")

    pkg = RechargePackage(name="包", price_cents=1000, credits=100)
    db_session.add(pkg)
    db_session.commit()

    order = PaymentOrder(
        user_id=user.id, package_id=pkg.id, out_trade_no="PAY_DASH_TEST",
        amount_cents=1000, credits_granted=100, status="paid", pay_method="pc_web",
        paid_at=datetime.now(timezone.utc),
    )
    db_session.add(order)
    db_session.commit()

    result = admin_service.get_dashboard(db_session)
    assert result["total_users"] == 1
    assert result["total_revenue_cents"] == 1000
    assert result["today_new_users"] == 1
    assert len(result["top_recharge_users"]) <= 10


# --- 配置 ---

def test_get_config():
    result = admin_service.get_config()
    assert "credits_per_token" in result
    assert "new_user_bonus_credits" in result


def test_update_config():
    from aigc_web import config
    orig_cpt = config.settings.CREDITS_PER_TOKEN
    orig_bonus = config.settings.NEW_USER_BONUS_CREDITS

    admin_service.update_config(config.settings, credits_per_token=2.0, new_user_bonus_credits=100)
    assert config.settings.CREDITS_PER_TOKEN == 2.0
    assert config.settings.NEW_USER_BONUS_CREDITS == 100

    # Restore original values to avoid leaking state into other tests
    config.settings.CREDITS_PER_TOKEN = orig_cpt
    config.settings.NEW_USER_BONUS_CREDITS = orig_bonus
