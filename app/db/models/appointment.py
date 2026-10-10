"""Appointments and consultation bookings model."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import PK_BIGINT, Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.service import Service
    from app.db.models.transaction import Transaction
    from app.db.models.user import User


class Appointment(Base, TimestampMixin):
    __tablename__ = "appointments"

    def __init__(self, **kw: Any) -> None:
        kw.setdefault("appointment_type", "online")
        kw.setdefault("status", "pending_payment")
        super().__init__(**kw)

    id: Mapped[int] = mapped_column(PK_BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True
    )

    appointment_type: Mapped[str] = mapped_column(
        String(20), default="online", nullable=False
    )  # online, offline
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending_payment", nullable=False
    )  # pending_payment, confirmed, completed, cancelled

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="appointments")
    service: Mapped["Service | None"] = relationship("Service", back_populates="appointments")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="appointment"
    )
