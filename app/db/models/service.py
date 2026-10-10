"""Service catalog model."""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.appointment import Appointment


class Service(Base):
    __tablename__ = "services"

    def __init__(self, **kw: Any) -> None:
        kw.setdefault("is_active", True)
        super().__init__(**kw)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title_uz: Mapped[str] = mapped_column(String(255), nullable=False)
    title_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    description_uz: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    service_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # consultation, audit, court, contract
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="service"
    )
