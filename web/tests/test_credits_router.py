# web/tests/test_credits_router.py
"""积分 API 集成测试。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from aigc_web.database import Base, get_db
from aigc_web.dependencies import set_verification_service
from aigc_web.main import app
from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.payment_order import PaymentOrder
from aigc_web.models.recharge_package import RechargePackage
from aigc_web.models.user import User
from aigc_web.services.payment import MockPaymentProvider, set_payment_provider
from aigc_web.services.sms import VerificationCodeService
from aigc_web.services.token import create_access_token

_db_session = None


@pytest.fixture
def client():
    global _db_session
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    _db_session = Session()

    sms = VerificationCodeService()
    set_verification_service(sms)
    set_payment_provider(MockPaymentProvider())

    def override_get_db():
        yield _db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    _db_session.close()
    engine.dispose()


def _db():
    return _db_session


def _create_user_and_login():
    db = _db()
    user = User(phone="13800138000", nickname="测试用户")
    db.add(user)
    db.commit()
    account = CreditAccount(user_id=user.id)
    db.add(account)
    db.commit()
    token = create_access_token(user.id)
    return token, user.id


def _seed_package():
    db = _db()
    pkg = RechargePackage(
        name="基础包",
        price_cents=1000,
        credits=100,
        bonus_credits=10,
        sort_order=1,
        is_active=True,
    )
    db.add(pkg)
    db.commit()
    return pkg.id


def test_list_packages(client):
    _seed_package()
    token, _ = _create_user_and_login()

    resp = client.get("/api/credits/packages", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "基础包"
    assert data[0]["price_cents"] == 1000


def test_get_balance(client):
    token, _ = _create_user_and_login()

    resp = client.get("/api/credits/balance", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["balance"] == 0
    assert data["total_recharged"] == 0


def test_create_recharge_order(client):
    pkg_id = _seed_package()
    token, _ = _create_user_and_login()

    resp = client.post(
        "/api/credits/recharge",
        json={"package_id": pkg_id, "pay_method": "pc_web"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "order_id" in data
    assert "pay_url" in data


def test_get_order_status(client):
    pkg_id = _seed_package()
    token, _ = _create_user_and_login()

    create_resp = client.post(
        "/api/credits/recharge",
        json={"package_id": pkg_id, "pay_method": "pc_web"},
        headers={"Authorization": f"Bearer {token}"},
    )
    order_id = create_resp.json()["order_id"]

    resp = client.get(
        f"/api/credits/orders/{order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


def test_payment_callback(client):
    """测试支付回调端点（MockPaymentProvider 验签总通过）。"""
    db = _db()
    user = User(phone="13800138100", nickname="回调用户")
    db.add(user)
    db.commit()
    account = CreditAccount(user_id=user.id)
    db.add(account)
    db.commit()

    pkg = RechargePackage(
        name="回调测试包", price_cents=500, credits=50, bonus_credits=0,
        sort_order=1, is_active=True,
    )
    db.add(pkg)
    db.commit()

    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no="PAY_CALLBACK_TEST",
        amount_cents=500,
        credits_granted=50,
        status="pending",
        pay_method="pc_web",
    )
    db.add(order)
    db.commit()

    resp = client.post(
        "/api/credits/payment/callback",
        data={"out_trade_no": "PAY_CALLBACK_TEST", "mock_sign": "ok"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "success"

    # 验证余额已更新
    db.refresh(account)
    assert account.balance == 50


def test_payment_callback_idempotent(client):
    """回调幂等：重复回调不重复加积分。"""
    db = _db()
    user = User(phone="13800138101", nickname="幂等用户")
    db.add(user)
    db.commit()
    account = CreditAccount(user_id=user.id)
    db.add(account)
    db.commit()

    pkg = RechargePackage(
        name="幂等测试包", price_cents=500, credits=50, bonus_credits=0,
        sort_order=1, is_active=True,
    )
    db.add(pkg)
    db.commit()

    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no="PAY_IDEMPOTENT_TEST",
        amount_cents=500,
        credits_granted=50,
        status="pending",
        pay_method="pc_web",
    )
    db.add(order)
    db.commit()

    # 第一次回调
    client.post("/api/credits/payment/callback", data={"out_trade_no": "PAY_IDEMPOTENT_TEST", "mock_sign": "ok"})
    # 第二次回调
    resp = client.post("/api/credits/payment/callback", data={"out_trade_no": "PAY_IDEMPOTENT_TEST", "mock_sign": "ok"})
    assert resp.status_code == 200

    db.refresh(account)
    assert account.balance == 50  # 不重复加


def test_get_transactions(client):
    token, _ = _create_user_and_login()

    resp = client.get(
        "/api/credits/transactions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_unauthorized_access(client):
    resp = client.get("/api/credits/balance")
    assert resp.status_code == 401
