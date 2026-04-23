# web/tests/test_order_timeout.py
"""订单超时关闭测试。"""

from datetime import datetime, timedelta, timezone

from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.payment_order import PaymentOrder
from aigc_web.models.recharge_package import RechargePackage
from aigc_web.models.user import User
from aigc_web.services import payment as payment_service


def _setup_data(db_session):
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


def _create_order(db_session, user, pkg, minutes_ago=0, out_trade_no=None):
    """创建测试订单，可指定创建时间为 N 分钟前。"""
    created_at = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no=out_trade_no or f"PAY_TIMEOUT_{user.id}",
        amount_cents=pkg.price_cents,
        credits_granted=pkg.credits + pkg.bonus_credits,
        status="pending",
        pay_method="pc_web",
        created_at=created_at,
    )
    db_session.add(order)
    db_session.commit()
    return order


def test_close_expired_orders(db_session):
    """超过 15 分钟的 pending 订单应被关闭。"""
    user, pkg = _setup_data(db_session)
    # 20 分钟前创建的订单
    _create_order(db_session, user, pkg, minutes_ago=20, out_trade_no="PAY_EXPIRED_001")

    closed = payment_service.close_expired_orders(db_session)
    assert closed == 1

    order = db_session.query(PaymentOrder).one()
    assert order.status == "closed"


def test_close_expired_orders_recent_order_not_closed(db_session):
    """5 分钟前创建的 pending 订单不应被关闭。"""
    user, pkg = _setup_data(db_session)
    _create_order(db_session, user, pkg, minutes_ago=5, out_trade_no="PAY_RECENT_001")

    closed = payment_service.close_expired_orders(db_session)
    assert closed == 0

    order = db_session.query(PaymentOrder).one()
    assert order.status == "pending"


def test_close_expired_orders_paid_not_closed(db_session):
    """已支付的订单不应被关闭。"""
    user, pkg = _setup_data(db_session)
    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no="PAY_PAID_001",
        amount_cents=pkg.price_cents,
        credits_granted=pkg.credits + pkg.bonus_credits,
        status="paid",
        pay_method="pc_web",
        created_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        paid_at=datetime.now(timezone.utc) - timedelta(minutes=28),
    )
    db_session.add(order)
    db_session.commit()

    closed = payment_service.close_expired_orders(db_session)
    assert closed == 0

    db_session.refresh(order)
    assert order.status == "paid"


def test_close_expired_orders_mixed(db_session):
    """混合场景：只有超时的 pending 被关闭。"""
    user, pkg = _setup_data(db_session)
    # 超时 pending
    _create_order(db_session, user, pkg, minutes_ago=20, out_trade_no="PAY_OLD_001")
    # 未超时 pending
    _create_order(db_session, user, pkg, minutes_ago=5, out_trade_no="PAY_NEW_001")

    closed = payment_service.close_expired_orders(db_session)
    assert closed == 1

    orders = db_session.query(PaymentOrder).order_by(PaymentOrder.id).all()
    assert orders[0].status == "closed"
    assert orders[1].status == "pending"


def test_close_expired_orders_empty(db_session):
    """无订单时不报错。"""
    closed = payment_service.close_expired_orders(db_session)
    assert closed == 0
