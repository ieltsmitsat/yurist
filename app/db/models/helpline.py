from typing import Any

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import PK_BIGINT, Base, TimestampMixin


class Helpline(Base, TimestampMixin):
    __tablename__ = "helplines"

    def __init__(self, **kw: Any) -> None:
        kw.setdefault("is_active", True)
        kw.setdefault("order", 0)
        super().__init__(**kw)

    id: Mapped[int] = mapped_column(PK_BIGINT, primary_key=True, autoincrement=True)
    category_uz: Mapped[str] = mapped_column(String(100), default="Boshqa", nullable=False)
    category_ru: Mapped[str] = mapped_column(String(100), default="Другие", nullable=False)
    organization_uz: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(50), nullable=False)
    description_uz: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description_ru: Mapped[str | None] = mapped_column(String(500), nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
