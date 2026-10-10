"""SQLAlchemy Declarative Base and common mixins."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Cross-dialect auto-incrementing BigInteger PK (PostgreSQL BIGSERIAL / SQLite INTEGER PRIMARY KEY)
PK_BIGINT = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    """Base declarative class for all models."""


class TimestampMixin:
    """Mixin adding created_at timestamp."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
