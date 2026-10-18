"""Service for routing and dispatching notifications to Telegram supergroup forum topics (threads)."""

import logging
from typing import TYPE_CHECKING

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.access_service import AccessService

if TYPE_CHECKING:
    from app.db.models.user import User

logger = logging.getLogger(__name__)


class GroupNotificationService:
    """Dispatches lead, contact, and payment notifications to configured supergroup forum topics."""

    @classmethod
    async def notify_new_lead(
        cls,
        bot: Bot,
        session: AsyncSession,
        user: "User",
        purpose: str,
    ) -> int:
        """Send new lead notification to all groups configured with lead_topic_id.

        Returns the number of successfully delivered messages.
        """
        destinations = await AccessService.get_topic_destinations(session, topic_type="lead")
        if not destinations:
            return 0

        clean_purpose = purpose.strip()
        if len(clean_purpose) > 1000:
            clean_purpose = clean_purpose[:997] + "..."

        text = (
            "📌 <b>YANGI LID / RO'YXATDAN O'TGAN MIJOZ</b>\n\n"
            f"👤 <b>Ismi:</b> {user.full_name or 'Noma\'lum'}\n"
            f"📱 <b>Telefon:</b> {user.phone_number or 'Kiritilmagan'}\n"
            f"🆔 <b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
            f"🌐 <b>Tili:</b> {user.language.upper()}\n\n"
            f"📝 <b>Yozishdan maqsadi / Savol:</b>\n"
            f"<i>{clean_purpose}</i>"
        )

        sent_count = 0
        for group_id, thread_id in destinations:
            try:
                await bot.send_message(
                    chat_id=group_id,
                    message_thread_id=thread_id,
                    text=text,
                )
                sent_count += 1
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "Failed to deliver lead notification to group %d (thread %d): %s",
                    group_id,
                    thread_id,
                    e,
                )

        return sent_count

    @classmethod
    async def notify_payment_receipt(
        cls,
        bot: Bot,
        session: AsyncSession,
        user: "User",
        photo_file_id: str,
        problem_summary: str = "",
        tx_id: int | None = None,
    ) -> int:
        """Send payment receipt screenshot to all groups configured with payment_topic_id.

        Returns the number of successfully delivered photos.
        """
        destinations = await AccessService.get_topic_destinations(session, topic_type="payment")
        if not destinations:
            return 0

        caption = (
            "💳 <b>YANGI TO'LOV CHEKI / SKRINSHOT</b>\n\n"
            f"👤 <b>Mijoz:</b> {user.full_name or 'Noma\'lum'}\n"
            f"📱 <b>Telefon:</b> {user.phone_number or 'Kiritilmagan'}\n"
            f"🆔 <b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
            f"🔢 <b>Tranzaksiya:</b> #{tx_id if tx_id else '—'}\n"
        )
        if problem_summary:
            snippet = problem_summary.strip()
            if len(snippet) > 400:
                snippet = snippet[:397] + "..."
            caption += f"\n📋 <b>Muammo / Xizmat:</b>\n<i>{snippet}</i>\n"

        caption += "\n👉 <i>Advokat to'lovni tasdiqlashi yoki tekshirishi kutilmoqda.</i>"

        sent_count = 0
        for group_id, thread_id in destinations:
            try:
                await bot.send_photo(
                    chat_id=group_id,
                    message_thread_id=thread_id,
                    photo=photo_file_id,
                    caption=caption,
                )
                sent_count += 1
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "Failed to deliver payment receipt to group %d (thread %d): %s",
                    group_id,
                    thread_id,
                    e,
                )

        return sent_count

    @classmethod
    async def notify_contact_request(
        cls,
        bot: Bot,
        session: AsyncSession,
        user: "User",
        service_title: str,
        problem_summary: str = "",
    ) -> int:
        """Send contact request to all groups configured with contact_topic_id.

        Returns the number of successfully delivered messages.
        """
        destinations = await AccessService.get_topic_destinations(session, topic_type="contact")
        if not destinations:
            return 0

        text = (
            "📞 <b>MIJOZ BILAN ALOQA (Advokat qo'ng'iroq qilishi uchun)</b>\n\n"
            f"👤 <b>Mijoz:</b> {user.full_name or 'Noma\'lum'}\n"
            f"📱 <b>Telefon:</b> {user.phone_number or 'Kiritilmagan'}\n"
            f"🆔 <b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
            f"💼 <b>Sotib olingan xizmat turi:</b> <b>{service_title}</b>\n"
        )
        if problem_summary:
            snippet = problem_summary.strip()
            if len(snippet) > 600:
                snippet = snippet[:597] + "..."
            text += f"\n📝 <b>Muammoning qisqacha tavsifi:</b>\n<i>{snippet}</i>\n"

        text += "\n⚠️ <i>Iltimos, mijoz bilan zudlik bilan bog'lanib, xizmat ko'rsatishni boshlang.</i>"

        sent_count = 0
        for group_id, thread_id in destinations:
            try:
                await bot.send_message(
                    chat_id=group_id,
                    message_thread_id=thread_id,
                    text=text,
                )
                sent_count += 1
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "Failed to deliver contact request to group %d (thread %d): %s",
                    group_id,
                    thread_id,
                    e,
                )

        return sent_count
