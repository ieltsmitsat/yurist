"""Chat message model for storing all user, bot, and lawyer conversations."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import PK_BIGINT, Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    def __init__(self, **kw: Any) -> None:
        kw.setdefault("sender_type", "user")
        kw.setdefault("message_type", "text")
        kw.setdefault("is_business", False)
        kw.setdefault("channel", "telegram")
        super().__init__(**kw)

    id: Mapped[int] = mapped_column(PK_BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(50), default="telegram", nullable=False)
    instagram_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # sender_type: "user", "bot", "lawyer"
    sender_type: Mapped[str] = mapped_column(String(20), default="user", nullable=False)

    # message_type: "text", "voice", "document"
    message_type: Mapped[str] = mapped_column(String(20), default="text", nullable=False)

    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_business: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="messages")

