"""Public helpline handlers with reply button catalogs and navigation."""

import logging

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.keyboards import helplines_categories_reply_kb, main_menu_kb
from app.db.models.helpline import Helpline
from app.db.models.user import User
from app.services.helpline_service import HelplineService

logger = logging.getLogger(__name__)

router = Router(name="helplines_router")
router.message.filter(F.chat.type == "private")


@router.message(F.text.in_(["📞 Ishonch telefon raqamlari", "📞 Телефоны доверия"]))
async def handle_helplines_menu(
    message: Message,
    session: AsyncSession,
    user: User | None = None,
) -> None:
    """Show public helpline categories as Reply Keyboard buttons."""
    lang = user.language if user else "uz"

    # Ensure defaults seeded if table was empty
    await HelplineService.seed_default_helplines(session)

    categories = await HelplineService.get_active_categories(session)

    if not categories:
        text = (
            "Hozircha ishonch telefonlari kiritilmagan."
            if lang == "uz"
            else "Телефоны доверия пока не добавлены."
        )
        await message.answer(text, reply_markup=main_menu_kb(lang))
        return

    text = (
        "📞 <b>Ishonch telefonlari katalogi</b>\n\n"
        "O'zbekistondagi davlat organlari, sudlar va favqulodda xizmatlarning rasmiy ishonch telefonlari bilan tanishish uchun quyidagi bo'limlardan birini tanlang:"
        if lang == "uz"
        else "📞 <b>Справочник телефонов доверия</b>\n\n"
        "Для просмотра официальных телефонов доверия государственных органов, судов и экстренных служб выберите нужный раздел:"
    )

    kb = helplines_categories_reply_kb(categories, lang)
    await message.answer(text, reply_markup=kb)


@router.message(F.text.in_(["🔙 Asosiy menyuga qaytish", "🔙 Главное меню"]))
async def handle_helpline_back_to_main(
    message: Message,
    user: User | None = None,
) -> None:
    """Return from helplines catalog to the main reply menu."""
    lang = user.language if user else "uz"
    text = (
        "Asosiy menyu:"
        if lang == "uz"
        else "Главное меню:"
    )
    await message.answer(text, reply_markup=main_menu_kb(lang))


@router.message(F.text.startswith("📂 "))
async def handle_helpline_category_click(
    message: Message,
    session: AsyncSession,
    user: User | None = None,
) -> None:
    """Display helplines for the selected category upon reply button click."""
    if not message.text:
        return

    raw_category = message.text[2:].strip()  # strip "📂 "
    lang = user.language if user else "uz"

    helplines = await HelplineService.get_by_category(session, raw_category)

    # If not found directly, try fetching by checking matching category names
    if not helplines:
        stmt = (
            select(Helpline)
            .where(
                Helpline.is_active.is_(True),
                (Helpline.category_uz.ilike(f"%{raw_category}%"))
                | (Helpline.category_ru.ilike(f"%{raw_category}%")),
            )
            .order_by(Helpline.order.asc(), Helpline.id.asc())
        )
        res = await session.execute(stmt)
        helplines = list(res.scalars().all())

    categories = await HelplineService.get_active_categories(session)
    reply_kb = helplines_categories_reply_kb(categories, lang)

    if not helplines:
        err_msg = (
            "Ushbu bo'limda hozircha telefon raqamlari mavjud emas."
            if lang == "uz"
            else "В данном разделе пока нет номеров."
        )
        await message.answer(err_msg, reply_markup=reply_kb)
        return

    cat_title = helplines[0].category_uz if lang == "uz" else helplines[0].category_ru

    text = f"📂 <b>{cat_title}</b>\n\n"
    for h in helplines:
        org_name = h.organization_uz if lang == "uz" else h.organization_ru
        desc_val = h.description_uz if lang == "uz" else h.description_ru
        desc = f"\n   ℹ️ <i>{desc_val}</i>" if desc_val else ""
        text += (
            f"🔹 <b>{org_name}</b>\n"
            f"   📞 <code>{h.phone_number}</code>{desc}\n\n"
        )

    text += (
        "<i>Boshqa bo'limni ko'rish uchun quyidagi tugmalardan birini bosing yoki asosiy menyuga qayting:</i>"
        if lang == "uz"
        else "<i>Чтобы посмотреть другой раздел, нажмите кнопку ниже или вернитесь в главное меню:</i>"
    )

    await message.answer(text, reply_markup=reply_kb)
