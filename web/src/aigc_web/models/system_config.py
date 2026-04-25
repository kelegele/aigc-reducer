"""系统配置 KV 持久化模型。"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from aigc_web.database import Base


class SystemConfig(Base):
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(256), nullable=False)
