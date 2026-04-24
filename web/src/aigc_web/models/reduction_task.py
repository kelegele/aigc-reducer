# web/src/aigc_web/models/reduction_task.py
"""改写任务 ORM 模型。"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aigc_web.database import Base


class ReductionTask(Base):
    __tablename__ = "reduction_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="parsing")
    detect_mode: Mapped[str] = mapped_column(String(10), nullable=False)
    style: Mapped[str] = mapped_column(String(20), nullable=False)
    full_reconstruct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    reduced_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 关系
    paragraphs: Mapped[list["ReductionParagraph"]] = relationship(
        "ReductionParagraph",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="ReductionParagraph.index",
    )
