"""Service for managing organization profile, contact, and payment settings."""

import logging
import re
import urllib.parse
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
    def extract_office_coordinates(office_address: str | None) -> tuple[float, float] | None:
        """Extract (latitude, longitude) from map URLs (Yandex, Google, 2GIS) or coordinates."""
        if not office_address:
            return None
        decoded = urllib.parse.unquote(office_address)

        # 1. Yandex: whatshere[point]=lon,lat or ll=lon,lat
        yandex_match = re.search(r"(?:whatshere\[point\]|ll)=([0-9.]+)[,\s]+([0-9.]+)", decoded)
        if yandex_match:
            p1, p2 = float(yandex_match.group(1)), float(yandex_match.group(2))
            if 36.0 <= p1 <= 46.0 and 55.0 <= p2 <= 75.0:
                return (p1, p2)
            if 36.0 <= p2 <= 46.0 and 55.0 <= p1 <= 75.0:
                return (p2, p1)

        # 2. Google / general: q=lat,lon or place/lat,lon or @lat,lon
        google_match = re.search(r"(?:q|place|center|@)=?([0-9.]+)[,\s]+([0-9.]+)", decoded)
        if google_match:
            p1, p2 = float(google_match.group(1)), float(google_match.group(2))
            if 36.0 <= p1 <= 46.0 and 55.0 <= p2 <= 75.0:
                return (p1, p2)
            if 36.0 <= p2 <= 46.0 and 55.0 <= p1 <= 75.0:
                return (p2, p1)

        # 3. Any two coordinate floats in text (e.g. 41.278871, 69.20197)
        coord_matches = re.findall(r"([0-9]{1,2}\.[0-9]{3,})[,\s]+([0-9]{1,3}\.[0-9]{3,})", decoded)
        for c1, c2 in coord_matches:
            p1, p2 = float(c1), float(c2)
            if 36.0 <= p1 <= 46.0 and 55.0 <= p2 <= 75.0:
                return (p1, p2)
            if 36.0 <= p2 <= 46.0 and 55.0 <= p1 <= 75.0:
                return (p2, p1)
            if -90.0 <= p1 <= 90.0 and -180.0 <= p2 <= 180.0:
                return (p1, p2)

        return None

    @staticmethod
    def get_clean_office_address(raw_address: str | None) -> str:
        """Return human-readable address text with raw URLs stripped out."""
        if not raw_address:
            return ""
        cleaned = re.sub(r"https?://\S+", "", raw_address).strip()
        cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip()
        return cleaned or raw_address

    @classmethod
    def format_office_address_text(cls, settings_record: OrgSettings, lang: str = "uz") -> str:
        """Format dynamic office address, contact phone, and working hours from admin settings."""
        clean_addr = cls.get_clean_office_address(settings_record.office_address)
        if lang == "ru":
            return (
                "🏢 <b>Информация о нашем офисе:</b>\n\n"
                f"📍 <b>Адрес:</b> {clean_addr}\n"
                f"📞 <b>Телефон:</b> {settings_record.contact_phone}\n"
                f"⏰ <b>График работы:</b> {settings_record.working_hours}\n\n"
                "<i>Вы можете посетить наш офис в рабочее время или связаться с нами по телефону.</i>"
            )
        return (
            "🏢 <b>Bizning ofisimiz ma'lumotlari:</b>\n\n"
            f"📍 <b>Manzil:</b> {clean_addr}\n"
            f"📞 <b>Telefon:</b> {settings_record.contact_phone}\n"
            f"⏰ <b>Ish vaqti:</b> {settings_record.working_hours}\n\n"
            "<i>Ish vaqtida ofisimizga tashrif buyurishingiz yoki huquqshunos bilan bog'lanishingiz mumkin.</i>"
        )

    @staticmethod
    def is_office_service_ref(transaction_ref: str | None) -> bool:
        """Check if transaction reference corresponds to in-person office consultation."""
        if not transaction_ref:
            return False
        ref = transaction_ref.lower()
        return any(k in ref for k in ["ofis", "office", "ko'rishib", "korishib"])

    @staticmethod
    def format_office_service_notice(lang: str = "uz") -> str:
        """Format notice that office address is provided after lawyer confirms payment for office consultation."""
        if lang == "ru":
            return (
                "🏢 <b>Очная консультация в офисе</b>\n\n"
                "Квалифицированный юрист и адвокат принимает клиентов в офисе по предварительной записи "
                "в рамках услуги <b>«Консультация с юристом и адвокатом в офисе»</b>.\n\n"
                "📌 <i>Точный адрес офиса, геолокация и время приема предоставляются сразу после того, "
                "как юрист подтвердит оплату данной услуги.</i>\n\n"
                "👉 Чтобы записаться на очную консультацию, выберите данную услугу из каталога."
            )
        return (
            "🏢 <b>Ofisda yuzma-yuz konsultatsiya</b>\n\n"
            "Malakali yurist va advokatimiz mijozlarni ofisda oldindan tayyorgarlik va yozilish asosida, "
            "<b>«Malakali yurist va advokatdan ofisda ko'rishib konsultatsiya olish»</b> xizmati doirasida qabul qiladi.\n\n"
            "📌 <i>Ofisimizning aniq manzili, lokatsiyasi va qabul vaqti faqat ushbu xizmat tanlanib, "
            "huquqshunos to'lovni tasdiqlaganidan so'ng darhol taqdim etiladi.</i>\n\n"
            "👉 Ofisda uchrashuvga yozilish uchun mavjud xizmatlar ro'yxatidan ushbu xizmatni tanlashingiz mumkin."
        )

    @classmethod
    def format_payment_confirmed_text(
        cls,
        transaction_ref: str | None,
        settings_record: OrgSettings,
        lang: str = "uz",
    ) -> str:
        """Format payment confirmation notification, revealing office address ONLY for office consultation."""
        if cls.is_office_service_ref(transaction_ref):
            clean_addr = cls.get_clean_office_address(settings_record.office_address)
            if lang == "ru":
                return (
                    "✅ <b>Ваш платеж успешно подтвержден!</b>\n\n"
                    f"💼 Услуга: <b>{transaction_ref or 'Консультация с юристом в офисе'}</b>\n\n"
                    f"📍 <b>Адрес нашего офиса:</b> {clean_addr}\n"
                    f"📞 <b>Телефон для связи:</b> {settings_record.contact_phone}\n"
                    f"⏰ <b>График работы:</b> {settings_record.working_hours}\n\n"
                    "⏰ <b>Пожалуйста, выберите удобное время визита:</b>\n"
                    "(Нажмите одну из кнопок ниже)"
                )
            return (
                "✅ <b>To'lovingiz muvaffaqiyatli tasdiqlandi!</b>\n\n"
                f"💼 Xizmat: <b>{transaction_ref or 'Ofisda yurist konsultatsiyasi'}</b>\n\n"
                f"📍 <b>Ofisimiz manzili:</b> {clean_addr}\n"
                f"📞 <b>Aloqa telefoni:</b> {settings_record.contact_phone}\n"
                f"⏰ <b>Qabul vaqti:</b> {settings_record.working_hours}\n\n"
                "⏰ <b>Iltimos, o'zingizga qulay tashrif vaqtini tanlang:</b>\n"
                "(Quyidagi tugmalardan birini bosing)"
            )

        if lang == "ru":
            return (
                "✅ <b>Ваш платеж успешно подтвержден!</b>\n\n"
                f"💼 Услуга: <b>{transaction_ref or 'Юридическая помощь'}</b>\n\n"
                "Оплата принята. В ближайшее время юрист свяжется с вами для оказания услуги."
            )
        return (
            "✅ <b>To'lovingiz muvaffaqiyatli tasdiqlandi!</b>\n\n"
            f"💼 Xizmat: <b>{transaction_ref or 'Yuridik xizmat'}</b>\n\n"
            "To'lov qabul qilindi. Tez orada mas'ul huquqshunosimiz siz bilan bog'lanib, xizmat ko'rsatishni boshlaydi."
        )

    @classmethod
    async def send_office_location(
        cls,
        bot: Any,
        chat_id: int,
        settings_record: OrgSettings,
        business_connection_id: str | None = None,
    ) -> bool:
        """Send native Telegram square location map card if coordinates exist in settings."""
        coords = cls.extract_office_coordinates(settings_record.office_address)
        if not coords:
            return False
        lat, lon = coords
        try:
            if business_connection_id:
                await bot.send_location(
                    chat_id=chat_id,
                    latitude=lat,
                    longitude=lon,
                    business_connection_id=business_connection_id,
                )
            else:
                await bot.send_location(
                    chat_id=chat_id,
                    latitude=lat,
                    longitude=lon,
                )
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not send native location to chat %s: %s", chat_id, e)
            try:
                await bot.send_location(chat_id=chat_id, latitude=lat, longitude=lon)
                return True
            except Exception as e2:  # noqa: BLE001
                logger.warning("Fallback send_location failed for chat %s: %s", chat_id, e2)
                return False

    @classmethod
    def detect_office_time_slot(cls, text: str) -> str | None:
        """Detect whether user text specifies morning (09:00-12:00) or afternoon (14:00-19:00) slot."""
        q = text.lower().strip()

        # 1. Direct interval matching
        if any(p in q for p in ["09:00 dan 12:00", "09:00-12:00", "9:00 dan 12:00", "9:00-12:00", "с 09:00 до 12:00"]):
            return "morning"
        if any(p in q for p in ["14:00 dan 19:00", "14:00-19:00", "с 14:00 до 19:00"]):
            return "afternoon"

        # 2. Keywords and hours with word boundary check
        has_morning = (
            any(k in q for k in ["ertalab", "tushgacha", "утром", "до обеда"])
            or bool(re.search(r"\b(?:0?9|10|11|12):00\b", q))
        )
        has_afternoon = (
            any(k in q for k in ["tushdan keyin", "kechqurun", "abeddan keyin", "после обеда", "вечером"])
            or bool(re.search(r"\b(?:14|15|16|17|18|19):00\b", q))
        )

        if has_morning and not has_afternoon:
            return "morning"
        if has_afternoon and not has_morning:
            return "afternoon"
        return None


    @classmethod
    def format_slot_confirmation(cls, slot_type: str, lang: str = "uz") -> tuple[str, str]:
        """Return human-readable slot text and confirmation reply message."""
        if slot_type == "morning":
            slot_text = "09:00 dan 12:00 gacha" if lang == "uz" else "с 09:00 до 12:00"
        else:
            slot_text = "14:00 dan 19:00 gacha" if lang == "uz" else "с 14:00 до 19:00"

        if lang == "ru":
            resp_text = (
                "✅ <b>Время визита успешно зарегистрировано!</b>\n\n"
                f"Вы успешно записаны на прием в нашем офисе на интервал <b>{slot_text}</b>.\n\n"
                "🤝 <b>Мы с нетерпением ждем вас в нашем офисе!</b> "
                "Наш юрист и адвокат будет полностью подготовлен к встрече с вами."
            )
        else:
            resp_text = (
                "✅ <b>Tashrif vaqti muvaffaqiyatli ro'yxatga olindi!</b>\n\n"
                f"Siz ofisimizga <b>{slot_text}</b> oralig'ida kelish uchun ro'yxatga olindingiz.\n\n"
                "🤝 <b>Sizni ofisimizda intizorlik bilan kutib qolamiz!</b> "
                "Malakali huquqshunosimiz siz bilan uchrashuvga to'liq tayyor bo'ladi."
            )
        return slot_text, resp_text

    @classmethod
    async def register_office_slot(
        cls,
        session: AsyncSession,
        user_id: int,
        slot_type: str,
        tx_id: int | None = None,
    ) -> tuple[str, str]:
        """Register appointment record and return slot_text and confirmation response text."""
        from datetime import UTC, datetime

        from app.db.models.appointment import Appointment
        from app.db.models.transaction import Transaction
        from app.db.models.user import User

        stmt_u = select(User).where(User.id == user_id)
        res_u = await session.execute(stmt_u)
        user = res_u.scalar_one_or_none()
        lang = user.language if user else "uz"

        slot_text, resp_text = cls.format_slot_confirmation(slot_type, lang=lang)

        appt = Appointment(
            user_id=user_id,
            appointment_type="offline",
            status="confirmed",
            scheduled_at=datetime.now(UTC),
        )
        session.add(appt)
        await session.commit()
        await session.refresh(appt)

        if tx_id:
            stmt_tx = select(Transaction).where(Transaction.id == tx_id)
            res_tx = await session.execute(stmt_tx)
            tx = res_tx.scalar_one_or_none()
            if tx:
                tx.appointment_id = appt.id
                await session.commit()

        return slot_text, resp_text

    @classmethod
    async def notify_office_slot_chosen(
        cls,
        bot: Any,
        session: AsyncSession,
        user_id: int,
        slot_text: str,
        tx_id: int | None = None,
    ) -> None:
        """Send topic notification to lawyer/admin group about chosen office consultation slot."""
        from app.core.config import settings
        from app.db.models.user import User
        from app.services.access_service import AccessService

        stmt_u = select(User).where(User.id == user_id)
        res_u = await session.execute(stmt_u)
        user = res_u.scalar_one_or_none()

        user_name = user.full_name if user else "Noma'lum"
        user_phone = user.phone_number if user and user.phone_number else "Kiritilmagan"
        tx_info = f"#{tx_id}" if tx_id else "Mavjud emas"

        notify_msg = (
            "📅 <b>OFISGA TASHRIF VAQTI TANLANDI</b>\n\n"
            f"👤 <b>Mijoz:</b> {user_name}\n"
            f"📱 <b>Telefon:</b> {user_phone}\n"
            f"⏰ <b>Tanlangan vaqt:</b> <b>{slot_text}</b>\n"
            f"🔢 <b>Tranzaksiya:</b> {tx_info}"
        )

        destinations = await AccessService.get_topic_destinations(session, "contact")
        if not destinations:
            destinations = await AccessService.get_topic_destinations(session, "payment")

        if destinations:
            for group_id, topic_id in destinations:
                try:
                    await bot.send_message(chat_id=group_id, text=notify_msg, message_thread_id=topic_id)
                except Exception as e:  # noqa: BLE001
                    logger.debug("Failed notifying topic %s in group %s: %s", topic_id, group_id, e)
        else:
            fallback_target = settings.ADMIN_GROUP_ID or settings.LAWYER_TELEGRAM_ID
            if fallback_target:
                try:
                    await bot.send_message(chat_id=fallback_target, text=notify_msg)
                except Exception as e:  # noqa: BLE001
                    logger.debug("Failed notifying fallback group/lawyer: %s", e)


