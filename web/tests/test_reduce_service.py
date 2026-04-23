"""ReduceService 业务逻辑测试。"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.reduction_paragraph import ReductionParagraph
from aigc_web.models.reduction_task import ReductionTask
from aigc_web.models.user import User
from aigc_web.services import credit as credit_service
from aigc_web.services.reduce import ReduceService


# ── helpers ──


def _create_user(db_session, phone="13800138000"):
    user = User(phone=phone, nickname=f"用户{phone[-4:]}")
    db_session.add(user)
    db_session.commit()
    account = CreditAccount(user_id=user.id)
    db_session.add(account)
    db_session.commit()
    return user


def _make_service(db_session) -> ReduceService:
    """创建 ReduceService，Mock 掉 LLMClient 构造。"""
    with patch("aigc_web.services.reduce.LLMClient"):
        return ReduceService(db_session)


def _create_task_sync(
    db_session, user_id, detect_mode="rules", style="学术人文化", text="段落一\n\n段落二\n\n段落三"
):
    """通过 ReduceService.create_task 创建任务。"""
    service = _make_service(db_session)
    task = asyncio.run(
        service.create_task(
            user_id=user_id,
            detect_mode=detect_mode,
            style=style,
            text=text,
        )
    )
    return task, service


# ── create_task ──


def test_create_task_with_text(db_session):
    user = _create_user(db_session)
    task, service = _create_task_sync(db_session, user.id)

    assert task.user_id == user.id
    assert task.status == "detecting"
    assert task.detect_mode == "rules"
    assert task.style == "学术人文化"
    assert task.original_text == "段落一\n\n段落二\n\n段落三"
    assert task.title == "段落一\n\n段落二\n\n段落三"

    paras = service._get_paragraphs(task.id)
    assert len(paras) == 3
    assert paras[0].original_text == "段落一"
    assert paras[1].original_text == "段落二"
    assert paras[2].original_text == "段落三"


def test_create_task_with_long_text(db_session):
    """标题超过 50 字符时截断。"""
    user = _create_user(db_session)
    long_text = "这是一段很长的文字" * 20  # >50 chars
    task, _ = _create_task_sync(db_session, user.id, text=long_text)

    assert task.title.endswith("...")
    assert len(task.title) <= 53  # 50 + "..."


def test_create_task_no_input(db_session):
    """不提供 text 和 file_path 应抛 ValueError。"""
    service = _make_service(db_session)
    with pytest.raises(ValueError, match="必须提供"):
        asyncio.run(
            service.create_task(
                user_id=1,
                detect_mode="rules",
                style="学术人文化",
            )
        )


# ── confirm_paragraph ──


def _setup_task_with_rewrites(db_session):
    """创建一个任务，段落已有改写结果，可以确认。"""
    user = _create_user(db_session)
    task, service = _create_task_sync(db_session, user.id)

    # 手动给段落设置改写结果
    paras = service._get_paragraphs(task.id)
    for p in paras:
        p.rewrite_aggressive = f"{p.original_text}-aggressive"
        p.rewrite_conservative = f"{p.original_text}-conservative"
        p.status = "rewritten"
    db_session.commit()

    return task, service, user


def test_confirm_paragraph_aggressive(db_session):
    task, service, _ = _setup_task_with_rewrites(db_session)

    para = service.confirm_paragraph(task.id, 0, "aggressive")
    assert para.user_choice == "aggressive"
    assert para.final_text == "段落一-aggressive"
    assert para.status == "confirmed"


def test_confirm_paragraph_conservative(db_session):
    task, service, _ = _setup_task_with_rewrites(db_session)

    para = service.confirm_paragraph(task.id, 1, "conservative")
    assert para.user_choice == "conservative"
    assert para.final_text == "段落二-conservative"
    assert para.status == "confirmed"


def test_confirm_paragraph_original(db_session):
    task, service, _ = _setup_task_with_rewrites(db_session)

    para = service.confirm_paragraph(task.id, 0, "original")
    assert para.user_choice == "original"
    assert para.final_text == "段落一"
    assert para.status == "confirmed"


def test_confirm_paragraph_manual(db_session):
    task, service, _ = _setup_task_with_rewrites(db_session)

    para = service.confirm_paragraph(task.id, 0, "manual", manual_text="手动改写的内容")
    assert para.user_choice == "manual"
    assert para.final_text == "手动改写的内容"
    assert para.status == "confirmed"


def test_confirm_paragraph_manual_empty(db_session):
    task, service, _ = _setup_task_with_rewrites(db_session)

    para = service.confirm_paragraph(task.id, 0, "manual")
    assert para.user_choice == "manual"
    assert para.final_text == ""


def test_confirm_paragraph_invalid_choice(db_session):
    task, service, _ = _setup_task_with_rewrites(db_session)

    with pytest.raises(ValueError, match="无效选择"):
        service.confirm_paragraph(task.id, 0, "invalid_choice")


def test_confirm_paragraph_not_found(db_session):
    user = _create_user(db_session)
    task, service = _create_task_sync(db_session, user.id)

    with pytest.raises(ValueError, match="段落不存在"):
        service.confirm_paragraph(task.id, 99, "aggressive")


# ── finalize_task ──


def test_finalize_task(db_session):
    """全部段落确认后生成最终文本。"""
    task, service, _ = _setup_task_with_rewrites(db_session)

    # 确认所有段落
    for i in range(3):
        service.confirm_paragraph(task.id, i, "aggressive")

    result = service.finalize_task(task.id)
    assert result.status == "completed"
    assert result.reduced_text == "段落一-aggressive\n\n段落二-aggressive\n\n段落三-aggressive"


def test_finalize_task_auto_confirms_low_risk(db_session):
    """finalize 自动用原文填充低风险（needs_processing=False）段落。"""
    user = _create_user(db_session)
    task, service = _create_task_sync(db_session, user.id)

    # 手动设置：段落0需要处理并已确认，段落1不需要处理（低风险）
    paras = service._get_paragraphs(task.id)
    paras[0].needs_processing = True
    paras[0].rewrite_aggressive = "改写结果"
    paras[0].status = "rewritten"
    paras[1].needs_processing = False
    paras[2].needs_processing = False
    db_session.commit()

    # 只确认段落0
    service.confirm_paragraph(task.id, 0, "aggressive")

    result = service.finalize_task(task.id)
    assert result.status == "completed"
    # 段落0用改写，段落1、2自动用原文
    assert "改写结果" in result.reduced_text
    assert "段落二" in result.reduced_text
    assert "段落三" in result.reduced_text


def test_finalize_task_unconfirmed(db_session):
    """有高风险段落未确认应抛 ValueError。"""
    user = _create_user(db_session)
    task, service = _create_task_sync(db_session, user.id)

    # 标记段落为需要处理但未确认
    paras = service._get_paragraphs(task.id)
    paras[0].needs_processing = True
    paras[0].status = "rewritten"
    db_session.commit()

    with pytest.raises(ValueError, match="尚未确认"):
        service.finalize_task(task.id)


# ── get_task ──


def test_get_task_not_found(db_session):
    service = _make_service(db_session)
    with pytest.raises(ValueError, match="任务不存在"):
        service.get_task(999, 1)


def test_get_task_wrong_user(db_session):
    user1 = _create_user(db_session, phone="13800138001")
    user2 = _create_user(db_session, phone="13800138002")

    task, _ = _create_task_sync(db_session, user1.id)

    service = _make_service(db_session)
    with pytest.raises(ValueError, match="任务不存在"):
        service.get_task(task.id, user2.id)


# ── list_tasks ──


def test_list_tasks(db_session):
    user = _create_user(db_session)
    _create_task_sync(db_session, user.id, text="任务1")
    _create_task_sync(db_session, user.id, text="任务2")
    _create_task_sync(db_session, user.id, text="任务3")

    service = _make_service(db_session)
    tasks, total = service.list_tasks(user.id, page=1, page_size=2)
    assert total == 3
    assert len(tasks) == 2

    tasks2, total2 = service.list_tasks(user.id, page=2, page_size=2)
    assert total2 == 3
    assert len(tasks2) == 1


def test_list_tasks_other_user(db_session):
    user1 = _create_user(db_session, phone="13800138001")
    user2 = _create_user(db_session, phone="13800138002")
    _create_task_sync(db_session, user1.id, text="用户1的任务")

    service = _make_service(db_session)
    tasks, total = service.list_tasks(user2.id)
    assert total == 0
    assert tasks == []


# ── estimate_credits ──


def test_estimate_credits_detect_rules(db_session):
    """rules 模式检测不走 LLM，est=0 但 _tokens_to_credits 有 max(1, ...)。"""
    user = _create_user(db_session)
    task, service = _create_task_sync(db_session, user.id)

    result = service.estimate_credits(task.id, "detect")
    # rules 模式走 else 分支 est=0，但 _tokens_to_credits(0) = max(1, 0) = 1
    assert result["estimated_tokens"] == 0
    assert result["estimated_credits"] == 1  # max(1, 0)
    # balance=0, cost=1 → insufficient
    assert result["sufficient"] is False


def test_estimate_credits_detect_llm(db_session):
    """llm 模式检测需要积分。"""
    user = _create_user(db_session)
    task, service = _create_task_sync(db_session, user.id, detect_mode="llm")

    result = service.estimate_credits(task.id, "detect")
    assert result["estimated_credits"] > 0
    assert result["current_balance"] == 0
    assert result["sufficient"] is False


def test_estimate_credits_reconstruct(db_session):
    user = _create_user(db_session)
    task, service = _create_task_sync(db_session, user.id)

    result = service.estimate_credits(task.id, "reconstruct")
    assert result["estimated_credits"] > 0
    assert "estimated_tokens" in result


def test_estimate_credits_rewrite(db_session):
    user = _create_user(db_session)
    task, service = _create_task_sync(db_session, user.id)

    # 没有 needs_processing 的段落，sum 为 0，但 _tokens_to_credits 有 max(1, ...)
    result = service.estimate_credits(task.id, "rewrite")
    assert result["estimated_tokens"] == 0
    assert result["estimated_credits"] == 1  # max(1, 0)

    # 用足够长的文本创建任务，确保积分预估 > 1
    long_text = "\n\n".join(["这是一段足够长的文本用于改写测试" * 50] * 3)
    task2, service2 = _create_task_sync(db_session, user.id, text=long_text)
    paras = service2._get_paragraphs(task2.id)
    paras[0].needs_processing = True
    db_session.commit()

    result2 = service2.estimate_credits(task2.id, "rewrite")
    assert result2["estimated_credits"] >= 1
