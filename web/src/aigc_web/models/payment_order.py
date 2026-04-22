# web/src/aigc_web/models/payment_order.py
"""支付订单 ORM 模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aigc_web.database import Base


class PaymentOrder(Base):
    __tablename__ = "payment_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    package_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recharge_packages.id"), nullable=False
    )
    out_trade_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    credits_granted: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    pay_method: Mapped[str] = mapped_column(String(20), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User")
    package: Mapped["RechargePackage"] = relationship("RechargePackage")
