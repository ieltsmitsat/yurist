"""Service for routing and dispatching notifications to Telegram supergroup forum topics (threads)."""

import logging
from typing import TYPE_CHECKING

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
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
        service_title: str = "Yuridik xizmat / Konsultatsiya",
        problem_summary: str = "",
        tx_id: int | None = None,
    ) -> int:
        """Send payment receipt screenshot to all groups configured with payment_topic_id.

        Includes full details and interactive inline buttons:
        - Tasdiqlash (pay_ok:<tx_id>)
        - Bekor qilish (pay_cancel:<tx_id>)
        """
        destinations = await AccessService.get_topic_destinations(session, topic_type="payment")
        if not destinations:
            return 0

        caption = (
            "💳 <b>YANGI TO'LOV CHEKI / SKRINSHOT</b>\n\n"
            f"👤 <b>Mijoz:</b> {user.full_name or 'Noma\'lum'}\n"
            f"📱 <b>Telefon:</b> {user.phone_number or 'Kiritilmagan'}\n"
            f"🆔 <b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
            f"💼 <b>Sotib olingan xizmat:</b> {service_title}\n"
        )
        if problem_summary:
            snippet = problem_summary.strip()
            if len(snippet) > 400:
                snippet = snippet[:397] + "..."
            caption += f"📝 <b>Mijoz muammosi haqida:</b>\n<i>{snippet}</i>\n"

        if tx_id:
            caption += f"\n🔢 <b>Tranzaksiya ID:</b> #{tx_id}\n"

        caption += "\n👉 <i>Quyidagi tugmalar orqali to'lovni tasdiqlang yoki bekor qiling:</i>"

        # Create inline keyboard for topic admins
        # Format: pay_ok:<tx_id> or pay_cancel:<tx_id>
        # Fallback to user_id if tx_id is None
        ok_data = f"pay_ok:tx_{tx_id}" if tx_id else f"pay_ok:u_{user.id}"
        cancel_data = f"pay_cancel:tx_{tx_id}" if tx_id else f"pay_cancel:u_{user.id}"

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ To'lovni tasdiqlash", callback_data=ok_data),
                    InlineKeyboardButton(text="❌ To'lovni bekor qilish", callback_data=cancel_data),
                ]
            ]
        )

        sent_count = 0
        for group_id, thread_id in destinations:
            try:
                await bot.send_photo(
                    chat_id=group_id,
                    message_thread_id=thread_id,
                    photo=photo_file_id,
                    caption=caption,
                    reply_markup=kb,
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
            "📞 <b>MIJOZ BILAN ALOQA (Huquqshunos qo'ng'iroq qilishi uchun)</b>\n\n"
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
