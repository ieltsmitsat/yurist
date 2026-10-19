"""User model representing bot users, leads and referrers."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import PK_BIGINT, Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.appointment import Appointment
    from app.db.models.chat_message import ChatMessage
    from app.db.models.inquiry import Inquiry
    from app.db.models.sos import SOSRequest
    from app.db.models.transaction import Transaction


class User(Base, TimestampMixin):
    __tablename__ = "users"

    def __init__(self, **kw: Any) -> None:
        kw.setdefault("lead_status", "new")
        kw.setdefault("language", "uz")
        kw.setdefault("free_questions_left", 3)
        kw.setdefault("is_subscribed", False)
        super().__init__(**kw)

    id: Mapped[int] = mapped_column(PK_BIGINT, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    language: Mapped[str] = mapped_column(String(10), default="uz", nullable=False)
    lead_status: Mapped[str] = mapped_column(String(50), default="new", nullable=False)
    business_connection_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Referral system
    referred_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    referral_code: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True, index=True
    )

    # Freemium and Subscription
    free_questions_left: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    is_subscribed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    subscription_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    referred_by: Mapped["User | None"] = relationship(
        "User", remote_side=[id], back_populates="referred_users"
    )
    referred_users: Mapped[list["User"]] = relationship("User", back_populates="referred_by")
    inquiries: Mapped[list["Inquiry"]] = relationship(
        "Inquiry", back_populates="user", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="user", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    sos_requests: Mapped[list["SOSRequest"]] = relationship(
        "SOSRequest", back_populates="user", cascade="all, delete-orphan"
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="user", cascade="all, delete-orphan"
    )
