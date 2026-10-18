"""Phone number capture and registration handler (Hard Gate with text & contact support)."""

import logging

from aiogram import Bot, F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.keyboards import main_menu_kb, phone_request_kb
from app.db.models.user import User
from app.services.referral_service import ReferralService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router(name="registration_router")
router.message.filter(F.chat.type == "private")


MENU_BUTTON_TEXTS: set[str] = {
    "💬 Yuridik savol berish",
    "💬 Задать правовой вопрос",
    "📑 Hujjat auditi",
    "📑 Аудит документа",
    "💼 Xizmatlar va Narxlar",
    "💼 Услуги и Цены",
    "👥 Taklif qilish (+1 savol)",
    "👥 Пригласить (+1 вопрос)",
    "🆘 Favqulodda yordam (SOS)",
    "🆘 Экстренная помощь (SOS)",
    "📞 Ishonch telefon raqamlari",
    "📞 Телефоны доверия",
    "⚙️ Sozlamalar",
    "⚙️ Настройки",
}


async def _complete_registration(
    message: Message,
    session: AsyncSession,
    bot: Bot,
    phone: str,
) -> None:
    """Save phone number, process referral reward, and send welcome onboarding message."""
    if not message.from_user:
        return

    updated_user = await UserService.update_phone(session, message.from_user.id, phone)
    if not updated_user:
        return

    lang = updated_user.language

    # Check and trigger referral reward if referred by friend
    reward_data = await ReferralService.process_referral_reward(session, updated_user)
    if reward_data:
        referrer_telegram_id, referrer_lang = reward_data
        try:
            ref_msg = (
                "🎉 <b>Xushxabar!</b> Siz taklif qilgan do'stingiz ro'yxatdan o'tdi.\n"
                "Sizning hisobingizga <b>+1 ta bepul yuridik tahlil</b> qo'shildi!"
                if referrer_lang == "uz"
                else "🎉 <b>Отличная новость!</b> Приглашенный вами друг зарегистрировался.\n"
                "На ваш баланс начислено <b>+1 бесплатная консультация</b>!"
            )
            await bot.send_message(chat_id=referrer_telegram_id, text=ref_msg)
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not notify referrer %d: %s", referrer_telegram_id, e)

    from app.services.chat_service import ChatService

    await ChatService.log_message(
        session=session,
        user_id=updated_user.id,
        telegram_id=updated_user.telegram_id,
        sender_type="user",
        text=f"📱 Telefon raqami: {phone}",
        message_type="contact" if message.contact else "text",
        telegram_message_id=message.message_id,
    )

    # Send welcome and main menu directly (replaces request_contact keyboard automatically)
    if lang == "uz":
        welcome_text = (
            f"✅ <b>Telefon raqamingiz muvaffaqiyatli tasdiqlandi:</b> <code>{updated_user.phone_number}</code>\n\n"
            f"🎁 Sizga dastlabki <b>{updated_user.free_questions_left} ta bepul yuridik tahlil</b> taqdim etildi.\n\n"
            "💬 <b>Endi savolingizni yo'llashingiz mumkin!</b>\n"
            "Marhamat, o'zingizni qiynayotgan huquqiy masalani matn ko'rinishida yozing yoki ovozli xabar (voice memo) yuboring.\n\n"
            "<i>Huquqshunos sizning savolingizni tahlil qilib, professional huquqiy xulosa taqdim etadi.</i>"
        )
    else:
        welcome_text = (
            f"✅ <b>Ваш номер успешно подтвержден:</b> <code>{updated_user.phone_number}</code>\n\n"
            f"🎁 Вам начислено <b>{updated_user.free_questions_left} бесплатных юридических консультации</b>.\n\n"
            "💬 <b>Теперь вы можете отправить ваш вопрос!</b>\n"
            "Опишите вашу ситуацию текстом или отправьте голосовое сообщение.\n\n"
            "<i>Юрист изучит ваш вопрос и предоставит квалифицированное заключение.</i>"
        )

    await message.answer(welcome_text, reply_markup=main_menu_kb(lang))
    await ChatService.log_message(
        session=session,
        user_id=updated_user.id,
        telegram_id=updated_user.telegram_id,
        sender_type="bot",
        text=welcome_text,
    )


@router.message(F.contact)
async def handle_contact_submission(
    message: Message,
    session: AsyncSession,
    bot: Bot,
    user: User | None = None,
) -> None:
    """Handle phone number contact submission (Hard Gate verification)."""
    if not message.from_user or not message.contact:
        return

    lang = user.language if user else "uz"

    # Anti-spoofing check: ensure user is sharing their own contact
    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        warn = (
            "⚠️ <b>Diqqat:</b> Iltimos, o'zingizning shaxsiy telefon raqamingizni yuboring.\n"
            "Buning uchun pastdagi tugmani bosing yoki raqamingizni yozib yuboring (Masalan: <code>+998 90 123 45 67</code>)."
            if lang == "uz"
            else "⚠️ <b>Внимание:</b> Пожалуйста, отправьте свой собственный номер телефона.\n"
            "Нажмите кнопку ниже или введите номер вручную (Например: <code>+998 90 123 45 67</code>)."
        )
        await message.answer(warn, reply_markup=phone_request_kb(lang))
        return

    raw_phone = message.contact.phone_number
    phone = UserService.normalize_phone_number(raw_phone) or f"+{raw_phone.lstrip('+')}"

    await _complete_registration(message, session, bot, phone)


@router.message(F.text, lambda msg, user=None: not user or not user.phone_number)
async def handle_text_phone_submission(
    message: Message,
    session: AsyncSession,
    bot: Bot,
    user: User | None = None,
) -> None:
    """Handle manually typed phone numbers for users who have not yet verified."""
    if not message.text or not message.from_user:
        return

    # Skip commands like /start and main menu buttons
    if message.text.startswith("/") or message.text in MENU_BUTTON_TEXTS:
        return

    normalized_phone = UserService.normalize_phone_number(message.text)
    lang = user.language if user else "uz"

    if normalized_phone:
        await _complete_registration(message, session, bot, normalized_phone)
        return

    # If message is not a valid phone number, kindly guide them
    prompt = (
        "Savolingizga javob berish va huquqshunos bilan aloqa o'rnatish uchun, "
        "iltimos, telefon raqamingizni pastdagi <b>«📱 Telefon raqamni yuborish»</b> "
        "tugmasi orqali yuboring yoki quyidagi formatda yozing:\n\n"
        "👉 <code>+998 90 123 45 67</code>"
        if lang == "uz"
        else "Для консультации и оперативной связи с юристом, "
        "пожалуйста, отправьте номер через кнопку <b>«📱 Отправить номер телефона»</b> "
        "или напишите в формате:\n\n"
        "👉 <code>+998 90 123 45 67</code>"
    )
    await message.answer(prompt, reply_markup=phone_request_kb(lang))
