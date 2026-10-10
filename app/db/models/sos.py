"""Emergency legal SOS requests model."""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import PK_BIGINT, Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User


class SOSRequest(Base, TimestampMixin):
    __tablename__ = "sos_requests"

    def __init__(self, **kw: Any) -> None:
        kw.setdefault("sos_type", "police_stop")
        kw.setdefault("status", "active")
        super().__init__(**kw)

    id: Mapped[int] = mapped_column(PK_BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    location_lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 8), nullable=True)
    location_lon: Mapped[Decimal | None] = mapped_column(Numeric(11, 8), nullable=True)
    sos_type: Mapped[str] = mapped_column(
        String(50), default="police_stop", nullable=False
    )  # police_stop, search_raid, detention, custom
    status: Mapped[str] = mapped_column(
        String(50), default="active", nullable=False
    )  # active, resolved, cancelled

    user: Mapped["User"] = relationship("User", back_populates="sos_requests")
