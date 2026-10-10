"""Inquiries and express audits model."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import PK_BIGINT, Base, TimestampMixin


class RiskLevel(str, enum.Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class InquiryStatus(str, enum.Enum):
    PENDING = "pending"
    ANSWERED = "answered"
    REVIEWING = "reviewing"
    APPROVED = "approved"


if TYPE_CHECKING:
    from app.db.models.attachment import Attachment
    from app.db.models.transaction import Transaction
    from app.db.models.user import User


class Inquiry(Base, TimestampMixin):
    __tablename__ = "inquiries"

    def __init__(self, **kw: Any) -> None:
        kw.setdefault("status", InquiryStatus.ANSWERED.value)
        super().__init__(**kw)

    id: Mapped[int] = mapped_column(PK_BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    question_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    stt_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Risk assessment
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)  # RiskLevel: none, low, medium, high
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-100

    # AI responses
    ai_draft_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_upsell_offer: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default=InquiryStatus.ANSWERED.value, nullable=False
    )  # InquiryStatus
    lawyer_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="inquiries")
    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment", back_populates="inquiry", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="inquiry"
    )
