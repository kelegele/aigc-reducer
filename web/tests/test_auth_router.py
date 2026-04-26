# web/tests/test_auth_router.py
"""Auth API 集成测试。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from aigc_web.config import settings
from aigc_web.database import Base, get_db
from aigc_web.dependencies import get_verification_service, set_verification_service
from aigc_web.main import app
from aigc_web.services.sms import VerificationCodeService


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    sms = VerificationCodeService()
    set_verification_service(sms)

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        # lifespan 会从 PostgreSQL 加载配置到 settings，覆盖测试默认值
        settings.NEW_USER_BONUS_CREDITS = 0
        settings.CREDITS_PER_1K_TOKENS = 1.0
        yield c

    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def _get_code(sms: VerificationCodeService, phone: str) -> str:
    """从 sms 服务内部取出验证码（测试用）。"""
    sms.send(phone)
    return sms._store[phone].code


def test_send_sms(client):
    resp = client.post("/api/auth/sms/send", json={"phone": "13800138000"})
    assert resp.status_code == 200
    assert resp.json()["message"] == "验证码已发送"


def test_send_sms_invalid_phone(client):
    resp = client.post("/api/auth/sms/send", json={"phone": "123"})
    assert resp.status_code == 422


def test_login_with_valid_code(client):
    sms = get_verification_service()
    code = _get_code(sms, "13800138001")

    resp = client.post(
        "/api/auth/login/phone", json={"phone": "13800138001", "code": code}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["phone"] == "13800138001"
    assert data["user"]["nickname"] == "用户8001"
    assert data["user"]["credit_balance"] == 0


def test_login_with_wrong_code(client):
    sms = get_verification_service()
    _get_code(sms, "13800138002")

    resp = client.post(
        "/api/auth/login/phone", json={"phone": "13800138002", "code": "000000"}
    )
    assert resp.status_code == 400


def test_get_me_with_valid_token(client):
    sms = get_verification_service()
    code = _get_code(sms, "13800138003")
    login_resp = client.post(
        "/api/auth/login/phone", json={"phone": "13800138003", "code": code}
    )
    token = login_resp.json()["access_token"]

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["phone"] == "13800138003"


def test_get_me_without_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_refresh_token(client):
    sms = get_verification_service()
    code = _get_code(sms, "13800138004")
    login_resp = client.post(
        "/api/auth/login/phone", json={"phone": "13800138004", "code": code}
    )
    refresh = login_resp.json()["refresh_token"]

    resp = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
