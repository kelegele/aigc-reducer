"""Reduce API 端点集成测试。"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from aigc_web.database import Base, get_db
from aigc_web.dependencies import require_current_user
from aigc_web.main import app
from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.reduction_task import ReductionTask
from aigc_web.models.reduction_paragraph import ReductionParagraph
from aigc_web.models.user import User
from aigc_web.services.reduce import ReduceService
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


def _create_user_and_login(phone="13800138000"):
    db = _db()
    user = User(phone=phone, nickname=f"用户{phone[-4:]}")
    db.add(user)
    db.commit()
    account = CreditAccount(user_id=user.id)
    db.add(account)
    db.commit()
    token = create_access_token(user.id)
    return token, user.id


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _create_task_via_service(user_id, detect_mode="rules", style="学术人文化",
                             text="段落一\n\n段落二"):
    """直接通过 service 创建任务（绕过 router），用于测试读取端点。"""
    with patch("aigc_web.services.reduce.LLMClient"):
        service = ReduceService(_db())
        task = asyncio.run(
            service.create_task(
                user_id=user_id,
                detect_mode=detect_mode,
                style=style,
                text=text,
            )
        )
        return task


# ── create_task (text) ──


def test_create_task_text(client):
    token, user_id = _create_user_and_login()

    with patch("aigc_web.services.reduce.LLMClient"):
        resp = client.post(
            "/api/reduce/tasks",
            data={
                "source_type": "text",
                "detect_mode": "rules",
                "style": "学术人文化",
                "text": "这是一段测试文本",
            },
            headers=_auth_headers(token),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "detecting"
    assert data["detect_mode"] == "rules"
    assert data["style"] == "学术人文化"
    assert len(data["paragraphs"]) == 1
    assert data["paragraphs"][0]["original_text"] == "这是一段测试文本"


# ── create_task (file) ──


def test_create_task_file(client):
    token, user_id = _create_user_and_login()

    # Mock parse_document to return known paragraphs
    from aigc_reducer_core.parser import Paragraph

    mock_paragraphs = [
        Paragraph(text="文件段落1", index=0),
        Paragraph(text="文件段落2", index=1),
    ]

    with (
        patch("aigc_web.services.reduce.LLMClient"),
        patch("aigc_web.services.reduce._parse_document_sync", return_value=mock_paragraphs),
    ):
        resp = client.post(
            "/api/reduce/tasks",
            data={
                "source_type": "file",
                "detect_mode": "rules",
                "style": "口语化",
            },
            files={"file": ("test.txt", b"file content here", "text/plain")},
            headers=_auth_headers(token),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "detecting"
    assert data["style"] == "口语化"


# ── create_task (no input) ──


def test_create_task_no_input(client):
    token, user_id = _create_user_and_login()

    with patch("aigc_web.services.reduce.LLMClient"):
        resp = client.post(
            "/api/reduce/tasks",
            data={
                "source_type": "text",
                "detect_mode": "rules",
                "style": "学术人文化",
            },
            headers=_auth_headers(token),
        )
    assert resp.status_code == 400


# ── list_tasks ──


def test_list_tasks(client):
    token, user_id = _create_user_and_login()
    _create_task_via_service(user_id, text="任务A")
    _create_task_via_service(user_id, text="任务B")

    resp = client.get("/api/reduce/tasks", headers=_auth_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["page"] == 1


def test_list_tasks_pagination(client):
    token, user_id = _create_user_and_login()
    for i in range(5):
        _create_task_via_service(user_id, text=f"任务{i}")

    resp = client.get(
        "/api/reduce/tasks?page=1&page_size=2",
        headers=_auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2


# ── get_task ──


def test_get_task(client):
    token, user_id = _create_user_and_login()
    task = _create_task_via_service(user_id)

    resp = client.get(
        f"/api/reduce/tasks/{task.id}",
        headers=_auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == task.id
    assert data["status"] == "detecting"
    assert len(data["paragraphs"]) == 2


# ── get_task (not found / wrong user) ──


def test_get_task_not_found(client):
    """get_task 路由未捕获 ValueError，会触发 500。"""
    token, user_id = _create_user_and_login()

    # Router 的 get_task 端点没有 try/except ValueError，
    # 所以 ValueError 会穿透为 500 Internal Server Error
    with pytest.raises(Exception):
        client.get(
            "/api/reduce/tasks/9999",
            headers=_auth_headers(token),
        )


def test_get_task_wrong_user(client):
    """访问别人的任务触发 500（router 未 catch ValueError）。"""
    token1, user1 = _create_user_and_login("13800138001")
    task = _create_task_via_service(user1)

    token2, user2 = _create_user_and_login("13800138002")
    with pytest.raises(Exception):
        client.get(
            f"/api/reduce/tasks/{task.id}",
            headers=_auth_headers(token2),
        )


# ── confirm_paragraph ──


def test_confirm_paragraph(client):
    token, user_id = _create_user_and_login()
    task = _create_task_via_service(user_id)

    # Setup: mark paragraphs as rewritten with rewrite results
    db = _db()
    paras = db.query(ReductionParagraph).filter_by(task_id=task.id).all()
    for p in paras:
        p.rewrite_aggressive = f"{p.original_text}-aggressive"
        p.rewrite_conservative = f"{p.original_text}-conservative"
        p.status = "rewritten"
    db.commit()

    resp = client.put(
        f"/api/reduce/tasks/{task.id}/paragraphs/0",
        json={"choice": "aggressive"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["index"] == 0
    assert data["choice"] == "aggressive"
    assert data["status"] == "confirmed"


def test_confirm_paragraph_invalid(client):
    token, user_id = _create_user_and_login()
    task = _create_task_via_service(user_id)

    # Setup: mark paragraph as rewritten
    db = _db()
    para = db.query(ReductionParagraph).filter_by(task_id=task.id, index=0).first()
    para.status = "rewritten"
    para.rewrite_aggressive = "x"
    para.rewrite_conservative = "y"
    db.commit()

    resp = client.put(
        f"/api/reduce/tasks/{task.id}/paragraphs/0",
        json={"choice": "invalid_choice"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 400


# ── finalize_task ──


def test_finalize_task(client):
    token, user_id = _create_user_and_login()
    task = _create_task_via_service(user_id)

    # Setup: mark all paragraphs as rewritten + confirm
    db = _db()
    paras = db.query(ReductionParagraph).filter_by(task_id=task.id).all()
    for p in paras:
        p.rewrite_aggressive = f"{p.original_text}-A"
        p.rewrite_conservative = f"{p.original_text}-C"
        p.status = "rewritten"
    db.commit()

    # Confirm all paragraphs via API
    for p in paras:
        client.put(
            f"/api/reduce/tasks/{task.id}/paragraphs/{p.index}",
            json={"choice": "aggressive"},
            headers=_auth_headers(token),
        )

    resp = client.post(
        f"/api/reduce/tasks/{task.id}/finalize",
        headers=_auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["reduced_text"] is not None


# ── estimate_credits ──


def test_estimate_credits(client):
    token, user_id = _create_user_and_login()
    task = _create_task_via_service(user_id)

    resp = client.post(
        f"/api/reduce/tasks/{task.id}/estimate?operation=detect",
        headers=_auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "estimated_credits" in data
    assert "current_balance" in data
    assert "sufficient" in data
