"""System access model for managing Lawyers, Notification Groups, and Admin permissions."""

from typing import Any

from sqlalchemy import BigInteger, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import PK_BIGINT, Base, TimestampMixin


class SystemAccess(Base, TimestampMixin):
    """Stores authorized actors in the system: multiple lawyers, admin groups, and dashboard admins."""

    __tablename__ = "system_access"

    def __init__(self, **kw: Any) -> None:
        kw.setdefault("is_active", True)
        kw.setdefault("role", "lawyer")
        super().__init__(**kw)

    id: Mapped[int] = mapped_column(PK_BIGINT, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="lawyer")  # "lawyer", "group", "admin"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Forum Supergroup Topic IDs (message_thread_id) for role="group"
    lead_topic_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    contact_topic_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    payment_topic_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
