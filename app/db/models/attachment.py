"""Attachments and uploaded legal documents/audio model."""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import PK_BIGINT, Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.inquiry import Inquiry


class Attachment(Base, TimestampMixin):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(PK_BIGINT, primary_key=True, autoincrement=True)
    inquiry_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("inquiries.id", ondelete="CASCADE"), nullable=False, index=True
    )

    file_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # pdf, docx, image, voice_ogg
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    inquiry: Mapped["Inquiry"] = relationship("Inquiry", back_populates="attachments")
