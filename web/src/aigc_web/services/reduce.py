# web/src/aigc_web/services/reduce.py
"""P3 检测/改写业务逻辑。"""

import asyncio
import json
import threading
from typing import AsyncGenerator

from sqlalchemy.orm import Session

from aigc_reducer_core import CancelledError
from aigc_reducer_core.detector import AIGCDetector
from aigc_reducer_core.llm_client import LLMClient
from aigc_reducer_core.parser import Paragraph
from aigc_reducer_core.rewriter import Rewriter

from aigc_web.config import settings
from aigc_web.models.reduction_paragraph import ReductionParagraph
from aigc_web.models.reduction_task import ReductionTask
from aigc_web.services import credit as credit_service


class ReduceService:
    """改写任务服务。"""

    def __init__(self, db: Session):
        self.db = db
        self._llm_client = LLMClient(
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )

    # ── 任务创建 ──

    async def create_task(
        self,
        user_id: int,
        detect_mode: str,
        style: str,
        text: str | None = None,
        file_path: str | None = None,
    ) -> ReductionTask:
        """创建改写任务。解析文本/文件为段落。"""
        # 1. 获取原文并解析段落
        if text:
            original_text = text
            paragraphs = [
                Paragraph(text=t.strip(), index=i)
                for i, t in enumerate(text.split("\n\n"))
                if t.strip()
            ]
        elif file_path:
            paragraphs = await asyncio.to_thread(
                _parse_document_sync, file_path
            )
            with open(file_path, "r", encoding="utf-8") as f:
                original_text = f.read()
        else:
            raise ValueError("必须提供 text 或 file_path")

        # 2. 创建任务记录
        title = (
            original_text[:50].replace("\n", " ") + "..."
            if len(original_text) > 50
            else original_text
        )
        task = ReductionTask(
            user_id=user_id,
            title=title,
            status="parsing",
            detect_mode=detect_mode,
            style=style,
            original_text=original_text,
        )
        self.db.add(task)
        self.db.flush()

        # 3. 创建段落记录
        for p in paragraphs:
            para = ReductionParagraph(
                task_id=task.id,
                index=p.index,
                original_text=p.text,
                is_heading=p.is_heading,
                has_formula=p.has_formula,
                has_code=p.has_code,
            )
            self.db.add(para)

        task.status = "detecting"
        self.db.commit()
        self.db.refresh(task)
        return task

    # ── 检测（SSE） ──

    async def start_detection(self, task_id: int) -> AsyncGenerator[dict, None]:
        """启动检测，SSE 生成器。"""
        task = self._get_task(task_id)
        if task.status != "detecting":
            yield {"type": "error", "message": f"任务状态不正确: {task.status}"}
            return

        paragraphs = self._get_paragraphs(task_id)
        parsed = [
            Paragraph(
                text=p.original_text,
                index=p.index,
                is_heading=p.is_heading,
                has_formula=p.has_formula,
                has_code=p.has_code,
            )
            for p in paragraphs
        ]

        # LLM 模式需要预检积分
        if task.detect_mode == "llm":
            est = self._estimate_tokens(parsed)
            cost = self._tokens_to_credits(est)
            balance = credit_service.get_balance(self.db, task.user_id)
            if balance < cost:
                yield {
                    "type": "error",
                    "message": f"积分不足，预计需要 {cost} 积分",
                }
                return

        # 执行检测
        cancel_event = threading.Event()
        detector = AIGCDetector(
            mode=task.detect_mode,
            cancel_event=cancel_event,
            llm_client=self._llm_client if task.detect_mode == "llm" else None,
        )

        try:
            results = await asyncio.to_thread(detector.analyze_all, parsed)
        except CancelledError:
            task.status = "failed"
            self.db.commit()
            yield {"type": "error", "message": "检测已取消"}
            return
        except Exception as e:
            task.status = "failed"
            self.db.commit()
            yield {"type": "error", "message": f"检测失败: {e}"}
            return

        # 保存检测结果
        total = len(results)
        needs_processing_count = 0
        for i, result in enumerate(results):
            para = paragraphs[i]
            para.detection_result = result
            para.risk_level = result.get("risk_level")
            para.needs_processing = result.get("risk_level") != "低风险"
            para.status = "detected"
            if para.needs_processing:
                needs_processing_count += 1

            yield {
                "type": "paragraph_done",
                "index": i,
                "risk_level": result.get("risk_level", ""),
                "composite_score": result.get("composite_score", 0),
                "current": i + 1,
                "total": total,
            }

        # LLM 模式扣费
        if task.detect_mode == "llm":
            est = self._estimate_tokens(parsed)
            cost = self._tokens_to_credits(est)
            credit_service.consume(
                self.db,
                task.user_id,
                est,
                ref_type="reduction_task",
                ref_id=task_id,
                remark="LLM 检测",
            )
            task.total_tokens += est
            task.total_credits += cost

        task.status = "detected"
        self.db.commit()

        yield {
            "type": "complete",
            "total_paragraphs": total,
            "needs_processing": needs_processing_count,
        }

    # ── 全量语义重构（SSE） ──

    async def start_reconstruction(self, task_id: int) -> AsyncGenerator[dict, None]:
        """全量语义重构（可选步骤）。"""
        task = self._get_task(task_id)
        if task.status != "detected":
            yield {"type": "error", "message": f"任务状态不正确: {task.status}"}
            return

        paragraphs = self._get_paragraphs(task_id)
        full_text = "\n\n".join(p.original_text for p in paragraphs)

        # 预检积分
        est = max(1, int(len(full_text) * 1.5))
        cost = self._tokens_to_credits(est)
        balance = credit_service.get_balance(self.db, task.user_id)
        if balance < cost:
            yield {
                "type": "error",
                "message": f"积分不足，预计需要 {cost} 积分",
            }
            return

        # 用 Rewriter 的风格做全量重构
        cancel_event = threading.Event()
        rewriter = Rewriter(
            task.style,
            llm_client=self._llm_client,
            cancel_event=cancel_event,
        )

        try:
            rewritten = await asyncio.to_thread(
                rewriter.rewrite_single,
                full_text,
                {"composite_score": 50},
                conservative=False,
            )
        except CancelledError:
            yield {"type": "error", "message": "重构已取消"}
            return
        except Exception as e:
            task.status = "failed"
            self.db.commit()
            yield {"type": "error", "message": f"重构失败: {e}"}
            return

        # 更新段落文本
        new_parts = rewritten.split("\n\n")
        for i, para in enumerate(paragraphs):
            if i < len(new_parts):
                para.original_text = new_parts[i].strip()

        # 扣费
        credit_service.consume(
            self.db,
            task.user_id,
            est,
            ref_type="reduction_task",
            ref_id=task_id,
            remark="全量重构",
        )
        task.total_tokens += est
        task.total_credits += cost
        task.full_reconstruct = True

        self.db.commit()
        yield {"type": "complete", "credits_used": cost}

    # ── 改写（SSE） ──

    async def start_rewrite(self, task_id: int) -> AsyncGenerator[dict, None]:
        """启动改写，SSE 生成器。对 needs_processing 的段落生成 A/B 选项。"""
        task = self._get_task(task_id)
        if task.status not in ("detected", "rewriting"):
            yield {"type": "error", "message": f"任务状态不正确: {task.status}"}
            return

        task.status = "rewriting"
        self.db.flush()

        paragraphs = [p for p in self._get_paragraphs(task_id) if p.needs_processing]
        if not paragraphs:
            # 没有需要改写的段落，直接标记完成
            task.status = "rewritten"
            self.db.commit()
            yield {"type": "complete", "total_credits_used": 0}
            return

        cancel_event = threading.Event()
        rewriter = Rewriter(
            task.style,
            llm_client=self._llm_client,
            cancel_event=cancel_event,
        )

        total = len(paragraphs)
        total_credits = 0

        for i, para in enumerate(paragraphs):
            # 逐段预检积分
            est = self._estimate_tokens_for_text(para.original_text) * 2  # A+B 两次调用
            cost = self._tokens_to_credits(est)
            balance = credit_service.get_balance(self.db, task.user_id)
            if balance < cost:
                task.status = "failed"
                self.db.commit()
                yield {
                    "type": "error",
                    "message": f"积分不足，段落 {i + 1} 预计需要 {cost} 积分",
                }
                return

            yield {"type": "progress", "current": i + 1, "total": total}

            detection = para.detection_result or {}

            try:
                aggressive = await asyncio.to_thread(
                    rewriter.rewrite_single,
                    para.original_text,
                    detection,
                    conservative=False,
                )
                conservative = await asyncio.to_thread(
                    rewriter.rewrite_single,
                    para.original_text,
                    detection,
                    conservative=True,
                )
            except CancelledError:
                task.status = "failed"
                self.db.commit()
                yield {"type": "error", "message": "改写已取消"}
                return
            except Exception as e:
                task.status = "failed"
                self.db.commit()
                yield {"type": "error", "message": f"改写失败: {e}"}
                return

            para.rewrite_aggressive = aggressive
            para.rewrite_conservative = conservative
            para.status = "rewritten"

            # 扣费
            credit_service.consume(
                self.db,
                task.user_id,
                est,
                ref_type="reduction_task",
                ref_id=task_id,
                remark=f"段落 {para.index} 改写",
            )
            total_credits += cost
            task.total_tokens += est
            task.total_credits += cost

            yield {
                "type": "paragraph_ready",
                "index": para.index,
                "aggressive": aggressive,
                "conservative": conservative,
            }

        task.status = "rewritten"
        self.db.commit()
        yield {"type": "complete", "total_credits_used": total_credits}

    # ── 段落确认 ──

    def confirm_paragraph(
        self,
        task_id: int,
        index: int,
        choice: str,
        manual_text: str | None = None,
    ) -> ReductionParagraph:
        """确认段落选择。"""
        para = (
            self.db.query(ReductionParagraph)
            .filter_by(task_id=task_id, index=index)
            .first()
        )
        if not para:
            raise ValueError(f"段落不存在: {index}")

        para.user_choice = choice
        if choice == "aggressive":
            para.final_text = para.rewrite_aggressive
        elif choice == "conservative":
            para.final_text = para.rewrite_conservative
        elif choice == "original":
            para.final_text = para.original_text
        elif choice == "manual":
            para.final_text = manual_text or ""
        else:
            raise ValueError(f"无效选择: {choice}")

        para.status = "confirmed"
        self.db.commit()
        return para

    # ── 任务完成 ──

    def finalize_task(self, task_id: int) -> ReductionTask:
        """所有段落确认后生成最终文档。"""
        task = self._get_task(task_id)
        paragraphs = self._get_paragraphs(task_id)

        for p in paragraphs:
            if p.status != "confirmed":
                if not p.needs_processing:
                    # 低风险段落自动用原文
                    p.final_text = p.original_text
                    p.status = "confirmed"
                    p.user_choice = "original"
                else:
                    raise ValueError(f"段落 {p.index} 尚未确认")

        # 拼接最终文本
        sorted_paras = sorted(paragraphs, key=lambda p: p.index)
        task.reduced_text = "\n\n".join(
            p.final_text for p in sorted_paras if p.final_text
        )
        task.status = "completed"
        self.db.commit()
        self.db.refresh(task)
        return task

    # ── 查询 ──

    def get_task(self, task_id: int, user_id: int) -> ReductionTask:
        """获取用户的任务。"""
        task = (
            self.db.query(ReductionTask)
            .filter_by(id=task_id, user_id=user_id)
            .first()
        )
        if not task:
            raise ValueError("任务不存在")
        return task

    def list_tasks(
        self, user_id: int, page: int = 1, page_size: int = 10
    ) -> tuple[list[ReductionTask], int]:
        """分页查询用户的改写任务。"""
        query = (
            self.db.query(ReductionTask)
            .filter_by(user_id=user_id)
            .order_by(ReductionTask.created_at.desc())
        )
        total = query.count()
        tasks = query.offset((page - 1) * page_size).limit(page_size).all()
        return tasks, total

    def estimate_credits(self, task_id: int, operation: str) -> dict:
        """预估积分消耗。"""
        task = self._get_task(task_id)
        paragraphs = self._get_paragraphs(task_id)

        if operation == "detect" and task.detect_mode == "llm":
            parsed = [
                Paragraph(text=p.original_text, index=p.index) for p in paragraphs
            ]
            est = self._estimate_tokens(parsed)
        elif operation == "reconstruct":
            total_chars = sum(len(p.original_text) for p in paragraphs)
            est = max(1, int(total_chars * 1.5))
        elif operation == "rewrite":
            needs = [p for p in paragraphs if p.needs_processing]
            est = sum(
                self._estimate_tokens_for_text(p.original_text) * 2 for p in needs
            )
        else:
            est = 0

        cost = self._tokens_to_credits(est)
        balance = credit_service.get_balance(self.db, task.user_id)

        return {
            "estimated_tokens": est,
            "estimated_credits": cost,
            "current_balance": balance,
            "sufficient": balance >= cost,
        }

    # ── 私有方法 ──

    def _get_task(self, task_id: int) -> ReductionTask:
        task = self.db.query(ReductionTask).filter_by(id=task_id).first()
        if not task:
            raise ValueError("任务不存在")
        return task

    def _get_paragraphs(self, task_id: int) -> list[ReductionParagraph]:
        return (
            self.db.query(ReductionParagraph)
            .filter_by(task_id=task_id)
            .order_by(ReductionParagraph.index)
            .all()
        )

    @staticmethod
    def _estimate_tokens(paragraphs: list[Paragraph]) -> int:
        total_chars = sum(len(p.text) for p in paragraphs)
        return max(1, int(total_chars * 1.5))

    @staticmethod
    def _estimate_tokens_for_text(text: str) -> int:
        return max(1, int(len(text) * 1.5))

    @staticmethod
    def _tokens_to_credits(token_count: int) -> int:
        return max(1, int(token_count / 1000 * settings.CREDITS_PER_TOKEN))


def _parse_document_sync(file_path: str) -> list[Paragraph]:
    """同步调用 parse_document，供 asyncio.to_thread 使用。"""
    from aigc_reducer_core.parser import parse_document

    return parse_document(file_path)
