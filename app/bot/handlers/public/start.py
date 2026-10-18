"""Start, language selection, and user settings handlers."""

import logging
from typing import Any

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.keyboards import (
    language_selection_kb,
    main_menu_kb,
    phone_request_kb,
    settings_kb,
)
from app.core.config import settings
from app.db.models.user import User
from app.services.access_service import AccessService
from app.services.referral_service import ReferralService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router(name="start_router")
router.message.filter(F.chat.type == "private")


@router.message(CommandStart())
async def handle_start(message: Message, session: AsyncSession, user: User | None = None) -> None:
    """Handle /start command with deep-link referral code."""
    if not message.from_user:
        return

    # Extract referral code if present (anti-fraud: prevent self-referral)
    referred_by_code = None
    if message.text and len(message.text.split()) > 1:
        code = message.text.split()[1].strip()
        if code != f"ref_{message.from_user.id}":
            referred_by_code = code

    # Get or create user
    current_user, is_new = await UserService.get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name,
        referred_by_code=referred_by_code,
    )

    # If new user or phone not yet set, offer language choice
    if is_new or not current_user.phone_number:
        greeting = (
            "Assalomu alaykum! Muloqot tilini tanlang:\n\n"
            "Здравствуйте! Выберите язык общения:"
        )
        from app.services.chat_service import ChatService

        await ChatService.log_message(
            session=session,
            user_id=current_user.id,
            telegram_id=current_user.telegram_id,
            sender_type="user",
            text=message.text or "/start",
        )
        await message.answer(greeting, reply_markup=language_selection_kb())
        await ChatService.log_message(
            session=session,
            user_id=current_user.id,
            telegram_id=current_user.telegram_id,
            sender_type="bot",
            text=greeting,
        )
    else:
        # Returning user with verified phone
        lang = current_user.language
        is_lawyer = UserService.is_lawyer(current_user)
        if is_lawyer:
            balance_line = (
                "🎁 Balansingiz: <b>Cheksiz (Advokat) ♾️</b>\n\n"
                if lang == "uz"
                else "🎁 Баланс: <b>Неограничен (Адвокат) ♾️</b>\n\n"
            )
        else:
            balance_line = (
                f"🎁 Balansingiz: <b>{current_user.free_questions_left} ta</b> bepul savol.\n\n"
                if lang == "uz"
                else f"🎁 Баланс: <b>{current_user.free_questions_left}</b> бесплатных вопроса.\n\n"
            )

        welcome = (
            f"Assalomu alaykum, <b>{current_user.full_name or 'hurmatli mijoz'}</b>!\n"
            f"{balance_line}"
            "Savolingizni yozing yoki menyudan kerakli bo'limni tanlang:"
            if lang == "uz"
            else f"Здравствуйте, <b>{current_user.full_name or 'уважаемый клиент'}</b>!\n"
            f"{balance_line}"
            "Напишите вопрос или выберите нужный раздел:"
        )
        
        # Log user command and bot response
        from app.services.chat_service import ChatService
        await ChatService.log_message(
            session, current_user.id, current_user.telegram_id, "user", message.text
        )
        
        await message.answer(welcome, reply_markup=main_menu_kb(lang))
        
        await ChatService.log_message(
            session, current_user.id, current_user.telegram_id, "bot", welcome
        )


@router.callback_query(F.data.startswith("set_lang:"))
async def handle_set_language(
    callback: CallbackQuery, session: AsyncSession, user: User | None = None
) -> None:
    """Handle language selection callback."""
    if not callback.data or not callback.from_user:
        return

    lang = callback.data.split(":")[1]
    await UserService.update_language(session, callback.from_user.id, lang)

    current_user = await UserService.get_by_telegram_id(session, callback.from_user.id)
    await callback.answer()

    if not isinstance(callback.message, Message):
        return

    # Hard gate: check if phone number is provided
    if not current_user or not current_user.phone_number:
        prompt = (
            "Til tanlandi: <b>O'zbekcha</b> 🇺🇿\n\n"
            "Konsultatsiyani faollashtirish uchun telefon raqamingizni yuboring:"
            if lang == "uz"
            else "Язык выбран: <b>Русский</b> 🇷🇺\n\n"
            "Для активации консультаций отправьте номер телефона:"
        )
        try:
            await callback.message.delete()
        except Exception as e:  # noqa: BLE001
            logger.debug("Could not delete message on language select: %s", e)
        await callback.message.answer(prompt, reply_markup=phone_request_kb(lang))
    else:
        confirm = (
            "✅ Muloqot tili o'zgartirildi: <b>O'zbekcha</b> 🇺🇿"
            if lang == "uz"
            else "✅ Язык общения изменен: <b>Русский</b> 🇷🇺"
        )
        await callback.message.edit_text(confirm, reply_markup=settings_kb(lang))
        await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_kb(lang))


def _format_settings_content(
    user: User,
    bot_username: str,
    is_lawyer: bool,
) -> tuple[str, Any]:
    """Helper to format profile text and keyboard for settings menu."""
    lang = user.language
    ref_link = ReferralService.get_referral_link(bot_username, user)
    balance_val = (
        "Cheksiz (Advokat) ♾️" if lang == "uz" else "Неограничен (Адвокат) ♾️"
    ) if is_lawyer else (
        f"{user.free_questions_left} ta" if lang == "uz" else f"{user.free_questions_left}"
    )

    if lang == "uz":
        info_text = (
            "⚙️ <b>Foydalanuvchi Sozlamalari va Profil</b>\n\n"
            f"👤 <b>Ism:</b> {user.full_name or 'Kiritilmagan'}\n"
            f"📱 <b>Telefon:</b> {user.phone_number or 'Tasdiqlanmagan'}\n"
            f"🌐 <b>Muloqot tili:</b> O'zbekcha 🇺🇿\n"
            f"🎁 <b>Bepul savollar balansi:</b> {balance_val}\n"
            f"🔗 <b>Taklif havolangiz:</b> <code>{ref_link}</code>\n\n"
            "Kerakli amalni tanlang:"
        )
    else:
        info_text = (
            "⚙️ <b>Настройки профиля</b>\n\n"
            f"👤 <b>Имя:</b> {user.full_name or 'Не указано'}\n"
            f"📱 <b>Телефон:</b> {user.phone_number or 'Не подтвержден'}\n"
            f"🌐 <b>Язык интерфейса:</b> Русский 🇷🇺\n"
            f"🎁 <b>Баланс консультаций:</b> {balance_val}\n"
            f"🔗 <b>Ваша реферальная ссылка:</b> <code>{ref_link}</code>\n\n"
            "Выберите действие:"
        )

    kb = settings_kb(lang)
    return info_text, kb


@router.message(F.text.in_(["⚙️ Sozlamalar", "⚙️ Настройки"]))
async def handle_settings_menu(
    message: Message, session: AsyncSession, bot: Bot, user: User | None = None
) -> None:
    """Display user account settings and language switch."""
    if not user:
        return

    bot_info = await bot.get_me()
    bot_username = bot_info.username or settings.BOT_USERNAME
    is_lawyer = UserService.is_lawyer(user) or await AccessService.is_lawyer(session, user.telegram_id)

    info_text, kb = _format_settings_content(user, bot_username, is_lawyer)
    await message.answer(info_text, reply_markup=kb)


@router.callback_query(F.data == "settings:change_lang")
async def handle_change_language_button(callback: CallbackQuery, user: User | None = None) -> None:
    """Show language selection keyboard from settings."""
    lang = user.language if user else "uz"
    prompt = (
        "Qaysi tilga o'zgartirmoqchisiz?\nВыберите язык:"
        if lang == "uz"
        else "Выберите язык интерфейса:\nQaysi tilga o'zgartirmoqchisiz?"
    )
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(prompt, reply_markup=language_selection_kb())
