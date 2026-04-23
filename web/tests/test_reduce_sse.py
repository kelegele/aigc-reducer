"""SSE 流式检测/改写测试。"""

import asyncio
import json
import threading
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from aigc_web.database import Base, get_db
from aigc_web.main import app
from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.reduction_paragraph import ReductionParagraph
from aigc_web.models.reduction_task import ReductionTask
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


def _create_detecting_task(user_id, detect_mode="rules", text="段落一\n\n段落二"):
    """直接通过 service 创建任务，状态为 detecting。"""
    with patch("aigc_web.services.reduce.LLMClient"):
        service = ReduceService(_db())
        task = asyncio.run(
            service.create_task(
                user_id=user_id,
                detect_mode=detect_mode,
                style="学术人文化",
                text=text,
            )
        )
        return task


def _collect_sse_events(resp):
    """从 SSE 响应中收集所有事件，返回 dict 列表。"""
    events = []
    for line in resp.iter_lines():
        if line.startswith("data: "):
            data_str = line[6:]
            events.append(json.loads(data_str))
    return events


# ── start_detection (rules mode) ──


def test_detection_rules_mode(client):
    """规则检测：Mock AIGCDetector.analyze_all 返回检测结果，验证 SSE 事件序列。"""
    token, user_id = _create_user_and_login()
    task = _create_detecting_task(user_id, detect_mode="rules")

    mock_results = [
        {"composite_score": 45, "risk_level": "中风险"},
        {"composite_score": 8, "risk_level": "低风险"},
    ]

    with (
        patch("aigc_web.services.reduce.LLMClient"),
        patch("aigc_web.services.reduce.AIGCDetector") as MockDetector,
    ):
        mock_instance = MagicMock()
        mock_instance.analyze_all.return_value = mock_results
        MockDetector.return_value = mock_instance

        with client.stream(
            "POST",
            f"/api/reduce/tasks/{task.id}/detect",
            headers=_auth_headers(token),
        ) as resp:
            assert resp.status_code == 200
            events = _collect_sse_events(resp)

    # 验证事件序列：2个 paragraph_done + 1个 complete
    assert events[0]["type"] == "paragraph_done"
    assert events[0]["index"] == 0
    assert events[0]["risk_level"] == "中风险"
    assert events[0]["current"] == 1
    assert events[0]["total"] == 2

    assert events[1]["type"] == "paragraph_done"
    assert events[1]["index"] == 1
    assert events[1]["risk_level"] == "低风险"
    assert events[1]["current"] == 2

    assert events[2]["type"] == "complete"
    assert events[2]["total_paragraphs"] == 2
    assert events[2]["needs_processing"] == 1  # 只有段落0需要处理

    # 验证数据库状态
    db = _db()
    db.refresh(task)
    assert task.status == "detected"

    paras = db.query(ReductionParagraph).filter_by(task_id=task.id).order_by(ReductionParagraph.index).all()
    assert paras[0].risk_level == "中风险"
    assert paras[0].needs_processing is True
    assert paras[0].status == "detected"
    assert paras[1].risk_level == "低风险"
    assert paras[1].needs_processing is False
    assert paras[1].status == "detected"


# ── start_detection (llm mode, insufficient credits) ──


def test_detection_llm_insufficient_credits(client):
    """LLM 模式检测但积分不足，返回错误事件。"""
    token, user_id = _create_user_and_login()
    # 用户余额为 0（默认）
    task = _create_detecting_task(user_id, detect_mode="llm")

    with (
        patch("aigc_web.services.reduce.LLMClient"),
        patch("aigc_web.services.reduce.AIGCDetector") as MockDetector,
    ):
        with client.stream(
            "POST",
            f"/api/reduce/tasks/{task.id}/detect",
            headers=_auth_headers(token),
        ) as resp:
            assert resp.status_code == 200
            events = _collect_sse_events(resp)

    # 应该只有一个 error 事件
    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "积分不足" in events[0]["message"]


# ── start_reconstruction ──


def test_reconstruction(client):
    """全量语义重构：Mock Rewriter，验证 SSE 事件。"""
    token, user_id = _create_user_and_login()
    task = _create_detecting_task(user_id)

    # 先把任务标记为 detected（reconstruct 要求 detected 状态）
    db = _db()
    task.status = "detected"
    db.commit()

    # 给用户充值积分（reconstruct 需要积分）
    from aigc_web.services import credit as credit_service
    credit_service.recharge(db, user_id, 1000, "test", 1, "测试充值")

    mock_rewritten = "重构后的段落1\n\n重构后的段落2"

    with (
        patch("aigc_web.services.reduce.LLMClient"),
        patch("aigc_web.services.reduce.Rewriter") as MockRewriter,
    ):
        mock_instance = MagicMock()
        mock_instance.rewrite_single.return_value = mock_rewritten
        MockRewriter.return_value = mock_instance

        with client.stream(
            "POST",
            f"/api/reduce/tasks/{task.id}/reconstruct",
            headers=_auth_headers(token),
        ) as resp:
            assert resp.status_code == 200
            events = _collect_sse_events(resp)

    assert len(events) == 1
    assert events[0]["type"] == "complete"
    assert events[0]["credits_used"] >= 1

    # 验证段落文本被更新
    db.refresh(task)
    assert task.full_reconstruct is True
    paras = db.query(ReductionParagraph).filter_by(task_id=task.id).order_by(ReductionParagraph.index).all()
    assert paras[0].original_text == "重构后的段落1"
    assert paras[1].original_text == "重构后的段落2"


# ── start_rewrite ──


def test_rewrite(client):
    """逐段改写：Mock Rewriter，验证 SSE 事件序列。"""
    token, user_id = _create_user_and_login()
    task = _create_detecting_task(user_id)

    # 准备：标记为 detected，段落标记 needs_processing
    db = _db()
    task.status = "detected"
    paras = db.query(ReductionParagraph).filter_by(task_id=task.id).order_by(ReductionParagraph.index).all()
    paras[0].needs_processing = True
    paras[0].detection_result = {"composite_score": 45, "risk_level": "中风险"}
    paras[1].needs_processing = True
    paras[1].detection_result = {"composite_score": 55, "risk_level": "中高"}
    db.commit()

    # 充值足够积分
    from aigc_web.services import credit as credit_service
    credit_service.recharge(db, user_id, 10000, "test", 1, "测试充值")

    def mock_rewrite_side_effect(text, detection, conservative=False):
        suffix = "-保守版" if conservative else "-激进版"
        return text + suffix

    with (
        patch("aigc_web.services.reduce.LLMClient"),
        patch("aigc_web.services.reduce.Rewriter") as MockRewriter,
    ):
        mock_instance = MagicMock()
        mock_instance.rewrite_single.side_effect = mock_rewrite_side_effect
        MockRewriter.return_value = mock_instance

        with client.stream(
            "POST",
            f"/api/reduce/tasks/{task.id}/rewrite",
            headers=_auth_headers(token),
        ) as resp:
            assert resp.status_code == 200
            events = _collect_sse_events(resp)

    # 事件序列：2x(progress + paragraph_ready) + 1x complete
    progress_events = [e for e in events if e["type"] == "progress"]
    ready_events = [e for e in events if e["type"] == "paragraph_ready"]
    complete_events = [e for e in events if e["type"] == "complete"]

    assert len(progress_events) == 2
    assert len(ready_events) == 2
    assert len(complete_events) == 1

    # 验证 progress 事件
    assert progress_events[0]["current"] == 1
    assert progress_events[0]["total"] == 2
    assert progress_events[1]["current"] == 2

    # 验证 paragraph_ready 事件
    assert ready_events[0]["aggressive"] == "段落一-激进版"
    assert ready_events[0]["conservative"] == "段落一-保守版"
    assert ready_events[1]["aggressive"] == "段落二-激进版"
    assert ready_events[1]["conservative"] == "段落二-保守版"

    # 验证 complete 事件
    assert complete_events[0]["total_credits_used"] >= 1

    # 验证数据库状态
    db.refresh(task)
    assert task.status == "rewritten"
    assert task.total_credits > 0

    paras = db.query(ReductionParagraph).filter_by(task_id=task.id).order_by(ReductionParagraph.index).all()
    assert paras[0].rewrite_aggressive == "段落一-激进版"
    assert paras[0].rewrite_conservative == "段落一-保守版"
    assert paras[0].status == "rewritten"
    assert paras[1].rewrite_aggressive == "段落二-激进版"
    assert paras[1].rewrite_conservative == "段落二-保守版"
    assert paras[1].status == "rewritten"
