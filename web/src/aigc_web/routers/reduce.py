# web/src/aigc_web/routers/reduce.py
"""P3 检测/改写路由。"""

import json as _json_module
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from aigc_web.database import get_db
from aigc_web.dependencies import require_current_user
from aigc_web.models.reduction_task import ReductionTask
from aigc_web.models.user import User
from aigc_web.schemas.reduce import (
    CreditsEstimateResponse,
    ParagraphChoiceRequest,
    TaskListResponse,
    TaskResponse,
)
from aigc_web.services.reduce import ReduceService

reduce_router = APIRouter(prefix="/api/reduce", tags=["reduce"])


@reduce_router.post("/tasks", response_model=TaskResponse)
async def create_task(
    source_type: str = Form(...),
    detect_mode: str = Form(...),
    style: str = Form(...),
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    service = ReduceService(db)

    file_path = None
    try:
        if source_type == "file":
            if not file:
                raise HTTPException(status_code=400, detail="请上传文件")
            # 保存上传文件到临时位置
            suffix = os.path.splitext(file.filename)[1] if file.filename else ".txt"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                content = await file.read()
                tmp.write(content)
                file_path = tmp.name
        elif source_type == "text":
            if not text:
                raise HTTPException(status_code=400, detail="请输入文本")
        else:
            raise HTTPException(status_code=400, detail="无效的 source_type")

        task = await service.create_task(
            user_id=current_user.id,
            detect_mode=detect_mode,
            style=style,
            text=text,
            file_path=file_path,
        )
        return _task_to_response(task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)


@reduce_router.get("/tasks", response_model=TaskListResponse)
def list_tasks(
    page: int = 1,
    page_size: int = 10,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    service = ReduceService(db)
    tasks, total = service.list_tasks(current_user.id, page, page_size, status, keyword)
    return {
        "items": [_task_to_list_item(t) for t in tasks],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@reduce_router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    service = ReduceService(db)
    task = service.get_task(task_id, current_user.id)
    return _task_to_response(task)


@reduce_router.post("/tasks/{task_id}/estimate", response_model=CreditsEstimateResponse)
def estimate_credits(
    task_id: str,
    operation: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    service = ReduceService(db)
    # 确保任务属于当前用户
    service.get_task(task_id, current_user.id)
    return service.estimate_credits(task_id, operation)


@reduce_router.post("/tasks/{task_id}/detect")
async def detect(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    service = ReduceService(db)
    # 确保任务属于当前用户
    service.get_task(task_id, current_user.id)

    async def event_generator():
        async for event in service.start_detection(task_id):
            yield f"data: {_json(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@reduce_router.post("/tasks/{task_id}/reconstruct")
async def reconstruct(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    service = ReduceService(db)
    service.get_task(task_id, current_user.id)

    async def event_generator():
        async for event in service.start_reconstruction(task_id):
            yield f"data: {_json(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@reduce_router.post("/tasks/{task_id}/rewrite")
async def rewrite(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    service = ReduceService(db)
    service.get_task(task_id, current_user.id)

    async def event_generator():
        async for event in service.start_rewrite(task_id):
            yield f"data: {_json(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@reduce_router.put("/tasks/{task_id}/paragraphs/{index}")
def confirm_paragraph(
    task_id: str,
    index: int,
    body: ParagraphChoiceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    service = ReduceService(db)
    # 确保任务属于当前用户
    service.get_task(task_id, current_user.id)
    try:
        para = service.confirm_paragraph(
            task_id, index, body.choice, body.manual_text
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "index": para.index,
        "choice": para.user_choice,
        "status": para.status,
    }


@reduce_router.post("/tasks/{task_id}/finalize", response_model=TaskResponse)
def finalize_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    service = ReduceService(db)
    # 确保任务属于当前用户
    service.get_task(task_id, current_user.id)
    try:
        task = service.finalize_task(task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _task_to_response(task)


@reduce_router.get("/tasks/{task_id}/export")
def export_task(
    task_id: str,
    format: str = "markdown",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    """导出任务结果。format: markdown | docx"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        service = ReduceService(db)
        task = service.get_task(task_id, current_user.id)
    except Exception as e:
        logger.error("[export] get_task failed: %s", e, exc_info=True)
        raise

    if task.status != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成，无法导出")

    if format == "docx":
        from aigc_web.services.reduce import export_docx

        buf = export_docx(task)
        filename = f"{task.title[:50] or 'result'}.docx"
        return Response(
            content=buf.read(),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # 默认 markdown
    content = task.reduced_text or ""
    filename = f"{task.title[:50] or 'result'}.md"
    return Response(
        content=content.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── 辅助函数 ──


def _json(obj) -> str:
    return _json_module.dumps(obj, ensure_ascii=False)


def _task_to_response(task: ReductionTask) -> dict:
    """将 ORM 模型转换为 TaskResponse dict。"""
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "detect_mode": task.detect_mode,
        "style": task.style,
        "full_reconstruct": task.full_reconstruct,
        "total_credits": task.total_credits,
        "original_text": task.original_text,
        "reduced_text": task.reduced_text,
        "created_at": task.created_at.isoformat() if task.created_at else "",
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "paragraphs": [
            {
                "index": p.index,
                "original_text": p.original_text,
                "is_heading": p.is_heading,
                "has_formula": p.has_formula,
                "has_code": p.has_code,
                "risk_level": p.risk_level,
                "composite_score": (
                    p.detection_result.get("composite_score")
                    if p.detection_result
                    else None
                ),
                "detection_detail": p.detection_result,
                "rewrite_aggressive": p.rewrite_aggressive,
                "rewrite_conservative": p.rewrite_conservative,
                "user_choice": p.user_choice,
                "final_text": p.final_text,
                "status": p.status,
            }
            for p in sorted(task.paragraphs, key=lambda x: x.index)
        ],
    }


def _task_to_list_item(task: ReductionTask) -> dict:
    """将 ORM 模型转换为 TaskListItem dict。"""
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "style": task.style,
        "total_credits": task.total_credits,
        "paragraph_count": len(task.paragraphs),
        "created_at": task.created_at.isoformat() if task.created_at else "",
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }
