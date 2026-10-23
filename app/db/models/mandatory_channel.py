from typing import Any

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import PK_BIGINT, Base, TimestampMixin


class MandatoryChannel(Base, TimestampMixin):
    """Channel or group required for mandatory user subscription."""

    __tablename__ = "mandatory_channels"

    def __init__(self, **kw: Any) -> None:
        kw.setdefault("is_active", True)
        kw.setdefault("order", 0)
        super().__init__(**kw)

    id: Mapped[int] = mapped_column(PK_BIGINT, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    chat_id: Mapped[str] = mapped_column(String(100), nullable=False)  # @channel_username or -100...
    url: Mapped[str] = mapped_column(String(500), nullable=False)  # https://t.me/...
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
