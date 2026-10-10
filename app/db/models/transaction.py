"""Transactions and payment ledger model (Safe abstraction compliant with off-limits rule)."""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import PK_BIGINT, Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.appointment import Appointment
    from app.db.models.inquiry import Inquiry
    from app.db.models.user import User


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    def __init__(self, **kw: Any) -> None:
        kw.setdefault("payment_status", "pending")
        super().__init__(**kw)

    id: Mapped[int] = mapped_column(PK_BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inquiry_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("inquiries.id", ondelete="SET NULL"), nullable=True
    )
    appointment_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # telegram_stars, p2p_card, payme, click
    payment_status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, completed, failed, refunded
    transaction_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    user: Mapped["User"] = relationship("User", back_populates="transactions")
    inquiry: Mapped["Inquiry | None"] = relationship("Inquiry", back_populates="transactions")
    appointment: Mapped["Appointment | None"] = relationship(
        "Appointment", back_populates="transactions"
    )
