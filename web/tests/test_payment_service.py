# web/tests/test_payment_service.py
"""支付服务单元测试。"""

from unittest.mock import MagicMock, patch

import pytest

from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.credit_transaction import CreditTransaction
from aigc_web.models.payment_order import PaymentOrder
from aigc_web.models.recharge_package import RechargePackage
from aigc_web.models.user import User
from aigc_web.services import payment as payment_service


def _setup_user_and_package(db_session):
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


@patch("aigc_web.services.payment.get_payment_provider")
def test_create_recharge_order(mock_get_provider, db_session):
    user, pkg = _setup_user_and_package(db_session)

    mock_provider = MagicMock()
    mock_provider.create_order.return_value = "https://pay.example.com/123"
    mock_get_provider.return_value = mock_provider

    result = payment_service.create_recharge_order(
        db_session, user.id, pkg.id, "pc_web"
    )

    assert result["order_id"] > 0
    assert result["pay_url"] == "https://pay.example.com/123"

    order = db_session.query(PaymentOrder).one()
    assert order.user_id == user.id
    assert order.package_id == pkg.id
    assert order.amount_cents == 1000
    assert order.credits_granted == 110  # 100 + 10 bonus
    assert order.status == "pending"
    assert order.pay_method == "pc_web"
    assert order.out_trade_no.startswith("PAY")


@patch("aigc_web.services.payment.get_payment_provider")
def test_create_recharge_order_inactive_package(mock_get_provider, db_session):
    user, pkg = _setup_user_and_package(db_session)
    pkg.is_active = False
    db_session.commit()

    with pytest.raises(ValueError, match="套餐不存在或已下架"):
        payment_service.create_recharge_order(db_session, user.id, pkg.id, "pc_web")


def test_handle_payment_callback_paid(db_session):
    user, pkg = _setup_user_and_package(db_session)

    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no="PAY_TEST_001",
        amount_cents=1000,
        credits_granted=110,
        status="pending",
        pay_method="pc_web",
    )
    db_session.add(order)
    db_session.commit()

    payment_service.handle_payment_callback(db_session, order.id)

    db_session.refresh(order)
    assert order.status == "paid"
    assert order.paid_at is not None

    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 110
    assert account.total_recharged == 110

    tx = db_session.query(CreditTransaction).one()
    assert tx.amount == 110
    assert tx.balance_after == 110
    assert tx.ref_type == "payment_order"
    assert tx.ref_id == order.id


def test_handle_payment_callback_idempotent(db_session):
    user, pkg = _setup_user_and_package(db_session)

    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no="PAY_TEST_002",
        amount_cents=1000,
        credits_granted=110,
        status="pending",
        pay_method="pc_web",
    )
    db_session.add(order)
    db_session.commit()

    # 第一次回调
    payment_service.handle_payment_callback(db_session, order.id)
    # 第二次回调（幂等）
    payment_service.handle_payment_callback(db_session, order.id)

    txs = db_session.query(CreditTransaction).all()
    assert len(txs) == 1  # 不重复加积分


def test_query_order_status(db_session):
    user, pkg = _setup_user_and_package(db_session)

    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no="PAY_TEST_003",
        amount_cents=1000,
        credits_granted=110,
        status="pending",
        pay_method="pc_web",
    )
    db_session.add(order)
    db_session.commit()

    result = payment_service.query_order_status(db_session, order.id, user.id)
    assert result["status"] == "pending"
    assert result["credits_granted"] == 110


def test_query_order_status_wrong_user(db_session):
    user, pkg = _setup_user_and_package(db_session)
    other_user = User(phone="13800138999", nickname="其他用户")
    db_session.add(other_user)
    db_session.commit()

    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no="PAY_TEST_004",
        amount_cents=1000,
        credits_granted=110,
        status="pending",
        pay_method="pc_web",
    )
    db_session.add(order)
    db_session.commit()

    with pytest.raises(ValueError, match="订单不存在"):
        payment_service.query_order_status(db_session, order.id, other_user.id)


def test_mock_provider_query_trade_returns_none():
    from aigc_web.services.payment import MockPaymentProvider
    provider = MockPaymentProvider()
    assert provider.query_trade("any_order") is None


@patch("aigc_web.services.payment.settings")
def test_alipay_provider_query_trade_paid(mock_settings):
    mock_settings.ALIPAY_APP_ID = "test-id"
    mock_settings.ALIPAY_PRIVATE_KEY = "key"
    mock_settings.ALIPAY_PUBLIC_KEY = "pub"
    mock_settings.ALIPAY_DEBUG = True

    from aigc_web.services.payment import AlipayProvider
    provider = AlipayProvider()
    provider._alipay = MagicMock()
    provider._alipay.api_alipay_trade_query.return_value = {
        "trade_status": "TRADE_SUCCESS",
        "trade_no": "ALIPAY_TRADE_123",
        "total_amount": "10.00",
    }

    result = provider.query_trade("PAY_TEST_001")
    assert result is not None
    assert result["status"] == "paid"
    assert result["trade_no"] == "ALIPAY_TRADE_123"


@patch("aigc_web.services.payment.settings")
def test_alipay_provider_query_trade_not_paid(mock_settings):
    mock_settings.ALIPAY_APP_ID = "test-id"
    mock_settings.ALIPAY_PRIVATE_KEY = "key"
    mock_settings.ALIPAY_PUBLIC_KEY = "pub"
    mock_settings.ALIPAY_DEBUG = True

    from aigc_web.services.payment import AlipayProvider
    provider = AlipayProvider()
    provider._alipay = MagicMock()
    provider._alipay.api_alipay_trade_query.return_value = {
        "trade_status": "WAIT_BUYER_PAY",
    }

    result = provider.query_trade("PAY_TEST_002")
    assert result is None


@patch("aigc_web.services.payment.settings")
def test_alipay_provider_query_trade_finished(mock_settings):
    """TRADE_FINISHED 也视为已支付。"""
    mock_settings.ALIPAY_APP_ID = "test-id"
    mock_settings.ALIPAY_PRIVATE_KEY = "key"
    mock_settings.ALIPAY_PUBLIC_KEY = "pub"
    mock_settings.ALIPAY_DEBUG = True

    from aigc_web.services.payment import AlipayProvider
    provider = AlipayProvider()
    provider._alipay = MagicMock()
    provider._alipay.api_alipay_trade_query.return_value = {
        "trade_status": "TRADE_FINISHED",
        "trade_no": "ALIPAY_TRADE_456",
        "total_amount": "20.00",
    }

    result = provider.query_trade("PAY_TEST_003")
    assert result is not None
    assert result["status"] == "paid"


@patch("aigc_web.services.payment.get_payment_provider")
def test_query_order_status_active_query_confirms_payment(mock_get_provider, db_session):
    """pending 订单查询时，后端主动调 query_trade，发现已支付则更新。"""
    user, pkg = _setup_user_and_package(db_session)
    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no="PAY_ACTIVE_001",
        amount_cents=1000,
        credits_granted=110,
        status="pending",
        pay_method="pc_web",
    )
    db_session.add(order)
    db_session.commit()

    mock_provider = MagicMock()
    mock_provider.query_trade.return_value = {
        "status": "paid",
        "trade_no": "ALIPAY_123",
        "paid_amount": "10.00",
    }
    mock_get_provider.return_value = mock_provider

    result = payment_service.query_order_status(db_session, order.id, user.id)
    assert result["status"] == "paid"
    assert result["paid_at"] is not None

    # 积分到账
    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 110

    # 幂等：再查一次不重复加积分
    result2 = payment_service.query_order_status(db_session, order.id, user.id)
    assert result2["status"] == "paid"
    assert db_session.query(CreditAccount).filter_by(user_id=user.id).one().balance == 110


@patch("aigc_web.services.payment.get_payment_provider")
def test_query_order_status_active_query_still_pending(mock_get_provider, db_session):
    """query_trade 返回 None（未支付），订单保持 pending。"""
    user, pkg = _setup_user_and_package(db_session)
    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no="PAY_ACTIVE_002",
        amount_cents=1000,
        credits_granted=110,
        status="pending",
        pay_method="pc_web",
    )
    db_session.add(order)
    db_session.commit()

    mock_provider = MagicMock()
    mock_provider.query_trade.return_value = None
    mock_get_provider.return_value = mock_provider

    result = payment_service.query_order_status(db_session, order.id, user.id)
    assert result["status"] == "pending"
