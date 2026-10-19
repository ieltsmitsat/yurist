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

    @staticmethod
    def is_office_address_inquiry(text: str) -> bool:
        """Detect if client is asking about office address, location, or how to visit."""
        q = text.lower().strip()
        keywords = [
            "manzil",
            "manzili",
            "manzilingiz",
            "manzilingizni",
            "lokatsiya",
            "lokatsiyangiz",
            "lokatsiyani",
            "joylashuv",
            "joylashgan",
            "adres",
            "adresingiz",
            "адрес",
            "адрес офиса",
            "где находится",
            "где вы находитесь",
            "где ваш офис",
            "где офис",
            "локация",
            "как проехать",
            "как добраться",
            "куда подъехать",
            "куда подойти",
        ]
        if any(k in q for k in keywords):
            return True

        phrases = [
            "ofis qayerda",
            "ofisingiz qayerda",
            "qayerdasizlar",
            "qayerda sizlar",
            "qayerga borsam",
            "qayerga borish",
            "qayerga borsak",
            "ofisga borish",
            "ofisga bormoqchiman",
        ]
        return any(p in q for p in phrases)

    @staticmethod
    def format_office_address_text(settings_record: OrgSettings, lang: str = "uz") -> str:
        """Format dynamic office address, contact phone, and working hours from admin settings."""
        if lang == "ru":
            return (
                "🏢 <b>Информация о нашем офисе:</b>\n\n"
                f"📍 <b>Адрес:</b> {settings_record.office_address}\n"
                f"📞 <b>Телефон:</b> {settings_record.contact_phone}\n"
                f"⏰ <b>График работы:</b> {settings_record.working_hours}\n\n"
                "<i>Вы можете посетить наш офис в рабочее время или связаться с нами по телефону.</i>"
            )
        return (
            "🏢 <b>Bizning ofisimiz ma'lumotlari:</b>\n\n"
            f"📍 <b>Manzil:</b> {settings_record.office_address}\n"
            f"📞 <b>Telefon:</b> {settings_record.contact_phone}\n"
            f"⏰ <b>Ish vaqti:</b> {settings_record.working_hours}\n\n"
            "<i>Ish vaqtida ofisimizga tashrif buyurishingiz yoki huquqshunos bilan bog'lanishingiz mumkin.</i>"
        )
