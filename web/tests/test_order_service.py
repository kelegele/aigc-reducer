# web/tests/test_order_service.py
"""订单服务单元测试。"""

import pytest

from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.credit_transaction import CreditTransaction
from aigc_web.models.payment_order import PaymentOrder
from aigc_web.models.recharge_package import RechargePackage
from aigc_web.models.user import User
from aigc_web.services import payment as payment_service


def _setup_data(db_session):
    """创建用户、积分账户、套餐。"""
    user = User(phone="13800138000", nickname="用户8000")
    db_session.add(user)
    db_session.commit()
    account = CreditAccount(user_id=user.id)
    db_session.add(account)
    db_session.commit()

    pkg = RechargePackage(
        name="基础包",
        price_cents=1000,
        credits=100,
        bonus_credits=10,
        sort_order=1,
        is_active=True,
    )
    db_session.add(pkg)
    db_session.commit()
    return user, pkg


def _create_order(db_session, user, pkg, status="pending", out_trade_no=None):
    """创建测试订单。"""
    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no=out_trade_no or f"PAY_TEST_{user.id}_{pkg.id}",
        amount_cents=pkg.price_cents,
        credits_granted=pkg.credits + pkg.bonus_credits,
        status=status,
        pay_method="pc_web",
    )
    db_session.add(order)
    db_session.commit()
    return order


def test_list_user_orders(db_session):
    user, pkg = _setup_data(db_session)
    _create_order(db_session, user, pkg, out_trade_no="PAY_LIST_001")
    _create_order(db_session, user, pkg, out_trade_no="PAY_LIST_002")

    result = payment_service.list_user_orders(db_session, user.id)
    assert result["total"] == 2
    assert len(result["items"]) == 2
    assert result["page"] == 1


def test_list_user_orders_status_filter(db_session):
    user, pkg = _setup_data(db_session)
    _create_order(db_session, user, pkg, status="pending", out_trade_no="PAY_FILT_001")
    _create_order(db_session, user, pkg, status="paid", out_trade_no="PAY_FILT_002")

    result = payment_service.list_user_orders(db_session, user.id, status="pending")
    assert result["total"] == 1
    assert result["items"][0]["out_trade_no"] == "PAY_FILT_001"


def test_list_user_orders_pagination(db_session):
    user, pkg = _setup_data(db_session)
    for i in range(5):
        _create_order(db_session, user, pkg, out_trade_no=f"PAY_PAGE_{i:03d}")

    page1 = payment_service.list_user_orders(db_session, user.id, page=1, size=2)
    assert len(page1["items"]) == 2
    assert page1["total"] == 5

    page3 = payment_service.list_user_orders(db_session, user.id, page=3, size=2)
    assert len(page3["items"]) == 1


def test_get_order_detail_user(db_session):
    user, pkg = _setup_data(db_session)
    order = _create_order(db_session, user, pkg, status="pending", out_trade_no="PAY_DET_001")

    detail = payment_service.get_order_detail(db_session, order.id, user_id=user.id)
    assert detail["id"] == order.id
    assert detail["package_name"] == "基础包"
    assert detail["credit_transaction_trade_no"] is None  # pending 无流水


def test_get_order_detail_with_transaction(db_session):
    user, pkg = _setup_data(db_session)
    order = _create_order(db_session, user, pkg, status="pending", out_trade_no="PAY_DET_TX_001")

    # 模拟支付回调写入积分（pending → paid）
    payment_service.handle_payment_callback(db_session, order.id)

    detail = payment_service.get_order_detail(db_session, order.id, user_id=user.id)
    assert detail["credit_transaction_trade_no"] is not None

    # 验证对账：流水确实关联到该订单
    tx = db_session.query(CreditTransaction).filter_by(trade_no=detail["credit_transaction_trade_no"]).one()
    assert tx.ref_type == "payment_order"
    assert tx.ref_id == str(order.id)


def test_get_order_detail_admin_mode(db_session):
    user, pkg = _setup_data(db_session)
    order = _create_order(db_session, user, pkg, out_trade_no="PAY_ADMIN_001")

    detail = payment_service.get_order_detail(db_session, order.id, user_id=None)
    assert detail["user_id"] == user.id
    assert detail["user_phone"] == "13800138000"
    assert detail["user_nickname"] == "用户8000"


def test_get_order_detail_wrong_user(db_session):
    user, pkg = _setup_data(db_session)
    other_user = User(phone="13800138999", nickname="其他用户")
    db_session.add(other_user)
    db_session.commit()

    order = _create_order(db_session, user, pkg, out_trade_no="PAY_WRONG_001")

    with pytest.raises(ValueError, match="订单不存在"):
        payment_service.get_order_detail(db_session, order.id, user_id=other_user.id)


def test_list_all_orders(db_session):
    user, pkg = _setup_data(db_session)
    _create_order(db_session, user, pkg, out_trade_no="PAY_ALL_001")

    result = payment_service.list_all_orders(db_session)
    assert result["total"] == 1
    item = result["items"][0]
    assert item["user_phone"] == "13800138000"
    assert item["package_name"] == "基础包"


def test_list_all_orders_search(db_session):
    user, pkg = _setup_data(db_session)
    _create_order(db_session, user, pkg, out_trade_no="PAY_SEARCH_001")

    # 按手机号搜索
    result = payment_service.list_all_orders(db_session, search="13800138000")
    assert result["total"] == 1

    # 按订单号搜索
    result = payment_service.list_all_orders(db_session, search="PAY_SEARCH")
    assert result["total"] == 1

    # 搜索不匹配
    result = payment_service.list_all_orders(db_session, search="不存在")
    assert result["total"] == 0


def test_list_all_orders_status_filter(db_session):
    user, pkg = _setup_data(db_session)
    _create_order(db_session, user, pkg, status="pending", out_trade_no="PAY_STATUS_001")
    _create_order(db_session, user, pkg, status="paid", out_trade_no="PAY_STATUS_002")

    result = payment_service.list_all_orders(db_session, status="paid")
    assert result["total"] == 1
    assert result["items"][0]["out_trade_no"] == "PAY_STATUS_002"
