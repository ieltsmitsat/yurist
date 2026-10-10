import logging

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.helpline import Helpline
from app.db.models.user import User

logger = logging.getLogger(__name__)

router = Router(name="helplines_router")
router.message.filter(F.chat.type == "private")


from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup


@router.message(F.text.in_(["📞 Ishonch telefon raqamlari", "📞 Телефоны доверия"]))
async def handle_helplines_menu(
    message: Message,
    session: AsyncSession,
    user: User | None = None,
) -> None:
    """Show public helpline categories."""
    lang = user.language if user else "uz"

    # Get unique categories
    stmt = select(Helpline.category_uz, Helpline.category_ru).where(Helpline.is_active == True).distinct()
    result = await session.execute(stmt)
    categories = result.fetchall()

    if not categories:
        text = (
            "Hozircha ishonch telefonlari kiritilmagan."
            if lang == "uz"
            else "Телефоны доверия пока не добавлены."
        )
        await message.answer(text)
        return

    # Create inline keyboard for categories
    buttons = []
    for cat_uz, cat_ru in categories:
        cat_name = cat_uz if lang == "uz" else cat_ru
        # Callbacks have size limits, use a short hash or safe string if needed, 
        # but categories are short enough: e.g. "Sud tizimi" -> "hc_Sud tizimi"
        # Let's map it safely by using UZ name as ID in callback since it's unique
        cb_data = f"hc_{cat_uz}"[:64] 
        buttons.append([InlineKeyboardButton(text=f"📂 {cat_name}", callback_data=cb_data)])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = (
        "📞 <b>Kerakli bo'limni tanlang:</b>"
        if lang == "uz"
        else "📞 <b>Выберите нужный раздел:</b>"
    )
    await message.answer(text, reply_markup=kb)

@router.callback_query(F.data == "hc_back_to_main")
async def handle_helpline_back(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User | None = None,
) -> None:
    """Go back to helpline categories."""
    lang = user.language if user else "uz"
    
    stmt = select(Helpline.category_uz, Helpline.category_ru).where(Helpline.is_active == True).distinct()
    result = await session.execute(stmt)
    categories = result.fetchall()

    buttons = []
    for cat_uz, cat_ru in categories:
        cat_name = cat_uz if lang == "uz" else cat_ru
        cb_data = f"hc_{cat_uz}"[:64]
        buttons.append([InlineKeyboardButton(text=f"📂 {cat_name}", callback_data=cb_data)])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = (
        "📞 <b>Kerakli bo'limni tanlang:</b>"
        if lang == "uz"
        else "📞 <b>Выберите нужный раздел:</b>"
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("hc_"))
async def handle_helpline_category(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User | None = None,
) -> None:
    """Show helplines for a specific category."""
    if not callback.data:
        return
    cat_uz = callback.data[3:]
    lang = user.language if user else "uz"

    stmt = select(Helpline).where(
        Helpline.is_active == True,
        Helpline.category_uz == cat_uz
    ).order_by(Helpline.order.asc())
    
    result = await session.execute(stmt)
    helplines = result.scalars().all()

    if not helplines:
        await callback.answer("Bo'sh / Пусто", show_alert=True)
        return

    # We will use category name from first item to display title
    cat_name = helplines[0].category_uz if lang == "uz" else helplines[0].category_ru

    text = f"📞 <b>{cat_name}:</b>\n\n"
    for h in helplines:
        org_name = h.organization_uz if lang == "uz" else h.organization_ru
        desc_val = h.description_uz if lang == "uz" else h.description_ru
        desc = f"\n   ℹ️ <i>{desc_val}</i>" if desc_val else ""
        text += f"🔹 <b>{org_name}</b>\n   📞 <code>{h.phone_number}</code>{desc}\n\n"

    # Add back button
    back_text = "🔙 Orqaga" if lang == "uz" else "🔙 Назад"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=back_text, callback_data="hc_back_to_main")]
    ])

    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()




