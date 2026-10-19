"""Referral program handlers (Invite a Friend, viral sharing, and real-time stats)."""

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.keyboards import referral_share_kb
from app.core.config import settings
from app.db.models.user import User
from app.services.referral_service import ReferralService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router(name="referral_router")
router.message.filter(F.chat.type == "private")


def format_referral_text(user: User, ref_link: str, stats: dict[str, int]) -> str:
    """Format bilingual referral dashboard with links, stats, and instructions."""
    lang = user.language
    is_lawyer = UserService.is_lawyer(user)
    balance_str = (
        "Cheksiz (Huquqshunos) ♾️" if lang == "uz" else "Неограниченно (Юрист) ♾️"
    ) if is_lawyer else (
        f"{user.free_questions_left} ta" if lang == "uz" else f"{user.free_questions_left} вопросов"
    )

    if lang == "uz":
        return (
            "👥 <b>Do'stlarni Taklif Qilish Dasturi</b>\n\n"
            "Yuridik yordamga muhtoj do'stlaringiz va yaqinlaringizni taklif qiling.\n"
            "Har bir taklif qilingan va telefonini tasdiqlagan do'stingiz uchun hisobingizga "
            "<b>+1 ta bepul yuridik tahlil</b> beriladi!\n\n"
            f"🔗 <b>Sizning shaxsiy taklif havolangiz:</b>\n<code>{ref_link}</code>\n\n"
            "📊 <b>Sizning ko'rsatkichlaringiz:</b>\n"
            f"• Jami taklif etilganlar: <b>{stats['total_invited']} kishi</b>\n"
            f"• Telefonini tasdiqlaganlar: <b>{stats['verified_count']} kishi</b>\n"
            f"• Qo'lga kiritilgan bonus savollar: <b>+{stats['bonus_earned']} ta</b>\n"
            f"• Joriy bepul savollar balansingiz: <b>{balance_str}</b>\n\n"
            "<i>Do'stlaringizga yuborish uchun pastdagi <b>«📤 Do'stlarga ulashish»</b> tugmasini bosing:</i>"
        )
    return (
        "👥 <b>Партнерская программа «Пригласи друга»</b>\n\n"
        "Поделитесь ссылкой с теми, кому нужна квалифицированная правовая помощь.\n"
        "За каждого приглашенного друга, подтвердившего номер, вам начисляется "
        "<b>+1 бесплатный вопрос</b>!\n\n"
        f"🔗 <b>Ваша реферальная ссылка:</b>\n<code>{ref_link}</code>\n\n"
        "📊 <b>Ваша статистика:</b>\n"
        f"• Всего переходов: <b>{stats['total_invited']}</b>\n"
        f"• Подтвержденных контактов: <b>{stats['verified_count']}</b>\n"
        f"• Начислено бонусов: <b>+{stats['bonus_earned']}</b>\n"
        f"• Ваш текущий баланс: <b>{balance_str}</b>\n\n"
        "<i>Чтобы отправить приглашение друзьям, нажмите кнопку <b>«📤 Поделиться с друзьями»</b> ниже:</i>"
    )


@router.message(F.text.in_(["👥 Taklif qilish (+1 savol)", "👥 Пригласить (+1 вопрос)"]))
async def handle_referral_menu(
    message: Message,
    session: AsyncSession,
    bot: Bot,
    user: User | None = None,
) -> None:
    """Display viral referral program link and statistics from reply keyboard."""
    if not user:
        return

    lang = user.language
    bot_user = await bot.get_me()
    bot_username = bot_user.username or settings.BOT_USERNAME

    ref_link = ReferralService.get_referral_link(bot_username, user)
    stats = await ReferralService.get_referral_stats(session, user)

    text = format_referral_text(user, ref_link, stats)
    await message.answer(text, reply_markup=referral_share_kb(ref_link, lang))


@router.callback_query(
    F.data.in_(["show_referral", "refresh_referral", "settings:show_referral"])
)
async def handle_referral_callback(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    user: User | None = None,
) -> None:
    """Handle referral callbacks from inline buttons (CTA, settings, and refresh)."""
    if not callback.from_user:
        return

    current_user = user or await UserService.get_by_telegram_id(session, callback.from_user.id)
    if not current_user:
        await callback.answer()
        return

    lang = current_user.language
    bot_user = await bot.get_me()
    bot_username = bot_user.username or settings.BOT_USERNAME

    ref_link = ReferralService.get_referral_link(bot_username, current_user)
    stats = await ReferralService.get_referral_stats(session, current_user)
    text = format_referral_text(current_user, ref_link, stats)
    kb = referral_share_kb(ref_link, lang)

    if callback.data == "refresh_referral":
        await callback.answer("✅ Yangilandi" if lang == "uz" else "✅ Обновлено")
        if isinstance(callback.message, Message):
            try:
                await callback.message.edit_text(text, reply_markup=kb)
            except TelegramBadRequest:
                # Content not modified
                pass
    else:
        chat = getattr(callback.message, "chat", None) if callback.message else None
        chat_type = getattr(chat, "type", "private") if chat else "private"
        if chat_type != "private":
            try:
                await bot.send_message(
                    chat_id=callback.from_user.id,
                    text=text,
                    reply_markup=kb,
                )
                await callback.answer(
                    "Taklif havolangiz shaxsiy bot chatiga yuborildi! 👥",
                    show_alert=True,
                )
                return
            except Exception:  # noqa: BLE001
                await callback.answer(
                    f"Taklif havolasini olish uchun botga kiring: @{bot_username}",
                    show_alert=True,
                )
                return

        await callback.answer()
        if isinstance(callback.message, Message):
            await callback.message.answer(text, reply_markup=kb)
