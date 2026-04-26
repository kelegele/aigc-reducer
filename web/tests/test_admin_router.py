# web/tests/test_admin_router.py
"""管理后台 API 集成测试。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from aigc_web.database import Base, get_db
from aigc_web.dependencies import set_verification_service
from aigc_web.main import app
from aigc_web.models.credit_account import CreditAccount
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


def _create_admin():
    db = _db()
    user = User(phone="13900000000", nickname="超管", is_admin=True)
    db.add(user)
    db.commit()
    account = CreditAccount(user_id=user.id)
    db.add(account)
    db.commit()
    return create_access_token(user.id), user.id


def _create_normal_user():
    db = _db()
    user = User(phone="13800138000", nickname="普通用户", is_admin=False)
    db.add(user)
    db.commit()
    account = CreditAccount(user_id=user.id)
    db.add(account)
    db.commit()
    return create_access_token(user.id)


def test_admin_access_allowed(client):
    token, _ = _create_admin()
    resp = client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_admin_access_forbidden(client):
    token = _create_normal_user()
    resp = client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_admin_access_no_token(client):
    resp = client.get("/api/admin/dashboard")
    assert resp.status_code == 401


def test_dashboard(client):
    token, _ = _create_admin()
    resp = client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    data = resp.json()
    assert data["total_users"] >= 0
    assert "top_recharge_users" in data


def test_crud_packages(client):
    token, _ = _create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    # 创建
    resp = client.post("/api/admin/packages", json={
        "name": "测试包", "price_cents": 500, "credits": 50,
    }, headers=headers)
    assert resp.status_code == 200
    pkg_id = resp.json()["id"]

    # 列表
    resp = client.get("/api/admin/packages", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # 修改
    resp = client.put(f"/api/admin/packages/{pkg_id}", json={"name": "改名"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "改名"

    # 删除
    resp = client.delete(f"/api/admin/packages/{pkg_id}", headers=headers)
    assert resp.status_code == 200


def test_list_users(client):
    token, _ = _create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/admin/users", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_list_users_search(client):
    token, _ = _create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/admin/users", params={"search": "13900000000"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_adjust_credits(client):
    token, admin_id = _create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put(f"/api/admin/users/{admin_id}/credits", json={
        "amount": 100, "remark": "测试加积分",
    }, headers=headers)
    assert resp.status_code == 200


def test_set_user_status(client):
    token, _ = _create_admin()
    headers = {"Authorization": f"Bearer {token}"}
    _create_normal_user()
    db = _db()
    user = db.query(User).filter(User.phone == "13800138000").first()

    resp = client.put(f"/api/admin/users/{user.id}/status", json={"is_active": False}, headers=headers)
    assert resp.status_code == 200


def test_get_config(client):
    token, _ = _create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/admin/config", headers=headers)
    assert resp.status_code == 200
    assert "credits_per_1k_tokens" in resp.json()


def test_update_config(client):
    token, _ = _create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put("/api/admin/config", json={"credits_per_1k_tokens": 2.0}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["credits_per_1k_tokens"] == 2.0

    # Restore
    client.put("/api/admin/config", json={"credits_per_1k_tokens": 1.0}, headers=headers)
