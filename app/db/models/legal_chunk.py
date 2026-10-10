"""Legal knowledge base chunks model for Lex.uz pgvector RAG."""

from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import PK_BIGINT, Base, TimestampMixin


class LegalChunk(Base, TimestampMixin):
    __tablename__ = "legal_chunks"

    id: Mapped[int] = mapped_column(PK_BIGINT, primary_key=True, autoincrement=True)
    law_title: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )  # e.g. "Fuqarolik kodeksi", "Mehnat kodeksi"
    article_number: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )  # e.g. "356-modda"
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    lex_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # Link to Lex.uz
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 1536 dimensions for text-embedding-3-small
    embedding = mapped_column(Vector(1536), nullable=True)
