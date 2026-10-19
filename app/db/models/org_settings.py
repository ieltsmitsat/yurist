"""Organization and payment profile settings model."""

from typing import Any

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import PK_BIGINT, Base, TimestampMixin


class OrgSettings(Base, TimestampMixin):
    """Stores configurable legal firm profile, contact info, and payment details."""

    __tablename__ = "org_settings"

    def __init__(self, **kw: Any) -> None:
        kw.setdefault("card_number", "9860 0001 2345 6789")
        kw.setdefault("card_holder", "Yuridik Xizmatlar")
        kw.setdefault("contact_phone", "+998 (71) 200-00-00")
        kw.setdefault("office_address", "Toshkent sh., Chilonzor tumani, Bunyodkor shoh ko'chasi, 15-uy")
        kw.setdefault("working_hours", "Dushanba — Shanba, 09:00 dan 18:00 gacha")
        super().__init__(**kw)

    id: Mapped[int] = mapped_column(PK_BIGINT, primary_key=True, autoincrement=True)
    card_number: Mapped[str] = mapped_column(String(50), default="9860 0001 2345 6789", nullable=False)
    card_holder: Mapped[str] = mapped_column(String(255), default="Yuridik Xizmatlar", nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(50), default="+998 (71) 200-00-00", nullable=False)
    office_address: Mapped[str] = mapped_column(
        Text,
        default="Toshkent sh., Chilonzor tumani, Bunyodkor shoh ko'chasi, 15-uy",
        nullable=False,
    )
    working_hours: Mapped[str] = mapped_column(
        String(255),
        default="Dushanba — Shanba, 09:00 dan 18:00 gacha",
        nullable=False,
    )
