# web/src/aigc_web/models/reduction_paragraph.py
"""改写段落 ORM 模型。"""

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aigc_web.database import Base


class ReductionParagraph(Base):
    __tablename__ = "reduction_paragraphs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reduction_tasks.id", ondelete="CASCADE"), nullable=False
    )
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_heading: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_formula: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_code: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    detection_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    needs_processing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rewrite_aggressive: Mapped[str | None] = mapped_column(Text, nullable=True)
    rewrite_conservative: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_choice: Mapped[str | None] = mapped_column(String(20), nullable=True)
    manual_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    # 关系
    task: Mapped["ReductionTask"] = relationship("ReductionTask", back_populates="paragraphs")
