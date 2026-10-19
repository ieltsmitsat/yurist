"""Service for managing organization profile, contact, and payment settings."""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.org_settings import OrgSettings

logger = logging.getLogger(__name__)


class OrgSettingsService:
    """Manages firm-wide dynamic configuration (payment card, contact phone, office address)."""

    @classmethod
    async def get_settings(cls, session: AsyncSession) -> OrgSettings:
        """Fetch current organization settings, creating default record if missing."""
        stmt = select(OrgSettings).order_by(OrgSettings.id.asc()).limit(1)
        res = await session.execute(stmt)
        settings_record = res.scalar_one_or_none()

        if not isinstance(settings_record, OrgSettings):
            settings_record = OrgSettings(
                card_number="9860 0001 2345 6789",
                card_holder="Yuridik Xizmatlar",
                contact_phone="+998 (71) 200-00-00",
                office_address="Toshkent sh., Chilonzor tumani, Bunyodkor shoh ko'chasi, 15-uy",
                working_hours="Dushanba — Shanba, 09:00 dan 18:00 gacha",
            )
            try:
                session.add(settings_record)
                await session.commit()
                await session.refresh(settings_record)
                logger.info("Initialized default OrgSettings with ID #%d", settings_record.id)
            except Exception as e:  # noqa: BLE001
                logger.debug("Default org settings init skipped: %s", e)

        return settings_record

    @classmethod
    async def update_settings(cls, session: AsyncSession, **kwargs: Any) -> OrgSettings:
        """Update organization settings."""
        settings_record = await cls.get_settings(session)

        for key, val in kwargs.items():
            if val is not None and hasattr(settings_record, key):
                setattr(settings_record, key, val)

        await session.commit()
        await session.refresh(settings_record)
        logger.info("Updated OrgSettings #%d: %s", settings_record.id, kwargs)
        return settings_record
