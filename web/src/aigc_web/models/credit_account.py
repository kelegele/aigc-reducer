# web/src/aigc_web/models/credit_account.py
"""积分账户 ORM 模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from aigc_web.database import Base


class CreditAccount(Base):
    __tablename__ = "credit_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False
    )
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_recharged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_consumed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", backref=backref("credit_account", uselist=False))
