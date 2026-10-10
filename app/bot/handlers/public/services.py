"""Services catalog and payment ledger handlers (Off-limits rule safe)."""

import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.keyboards import payment_methods_kb, services_catalog_kb
from app.core.config import settings
from app.db.models.user import User
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

router = Router(name="services_router")
router.message.filter(F.chat.type == "private")


def format_service_details_text(service_title: str, service_desc: str | None, price_fmt: str, lang: str) -> str:
    """Format structured legal service card with deliverables, guarantees, and pricing."""
    if lang == "uz":
        return (
            f"💼 <b>{service_title}</b>\n\n"
            f"{service_desc or 'Professional advokatlik xizmati.'}\n\n"
            f"💵 <b>Rasmiy narxi:</b> {price_fmt}\n"
            "🛡 <b>Kafolat:</b> Rasmiy advokatlik orderi/shartnomasi va to'liq maxfiylik.\n"
            "⏱ <b>Bajarilish muddati:</b> To'lov tasdiqlangach 24 soat ichida (yoki kelishuv asosida).\n\n"
            "<i>Quyidagi to'lov yoki bog'lanish usulini tanlang:</i>"
        )
    return (
        f"💼 <b>{service_title}</b>\n\n"
        f"{service_desc or 'Квалифицированная юридическая помощь.'}\n\n"
        f"💵 <b>Стоимость:</b> {price_fmt}\n"
        "🛡 <b>Гарантия:</b> Официальный адвокатский договор и полная конфиденциальность.\n"
        "⏱ <b>Срок исполнения:</b> В течение 24 часов после оплаты (или по договоренности).\n\n"
        "<i>Выберите способ оплаты или связи с адвокатом:</i>"
    )


@router.message(F.text.in_(["💼 Xizmatlar va Narxlar", "💼 Услуги и Цены"]))
async def handle_services_menu(
    message: Message, session: AsyncSession, user: User | None = None
) -> None:
    """Display active legal services catalog."""
    lang = user.language if user else "uz"
    services = await PaymentService.get_active_services(session)

    if not services:
        await PaymentService.seed_default_services(session)
        services = await PaymentService.get_active_services(session)

    intro = (
        "💼 <b>Yuridik Xizmatlar va Rasmiy Tariflar</b>\n\n"
        "Malakali advokatlar tomonidan ko'rsatiladigan professional huquqiy xizmatlar bilan tanishing va o'zingizga keraklisini tanlang:\n\n"
        "✅ Rasmiy advokatlik shartnomasi va orderi\n"
        "✅ 100% maxfiylik va himoya kafolati\n"
        "✅ Qonuniy asoslangan professional yondashuv"
        if lang == "uz"
        else "💼 <b>Юридические Услуги и Тарифы</b>\n\n"
        "Ознакомьтесь с перечнем профессиональных правовых услуг и выберите нужный тариф:\n\n"
        "✅ Официальный адвокатский договор и ордер\n"
        "✅ 100% конфиденциальность и защита ваших прав\n"
        "✅ Опытные лицензированные специалисты"
    )
    await message.answer(intro, reply_markup=services_catalog_kb(services, lang))


@router.callback_query(F.data == "back_to_services")
async def handle_back_to_services(
    callback: CallbackQuery, session: AsyncSession, user: User | None = None
) -> None:
    """Return to legal services catalog menu."""
    if not callback.message:
        return

    lang = user.language if user else "uz"
    services = await PaymentService.get_active_services(session)
    if not services:
        await PaymentService.seed_default_services(session)
        services = await PaymentService.get_active_services(session)

    intro = (
        "💼 <b>Yuridik Xizmatlar va Rasmiy Tariflar</b>\n\n"
        "Kerakli xizmat turini tanlang:"
        if lang == "uz"
        else "💼 <b>Юридические Услуги и Тарифы</b>\n\n"
        "Выберите интересующую вас услугу:"
    )
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(intro, reply_markup=services_catalog_kb(services, lang))


@router.callback_query(F.data.startswith("buy_service:"))
async def handle_buy_service(
    callback: CallbackQuery, session: AsyncSession, user: User | None = None
) -> None:
    """Display service details and safe payment options."""
    if not callback.message or not callback.data:
        return

    service_id = int(callback.data.split(":")[1])
    service = await PaymentService.get_service_by_id(session, service_id)
    if not service:
        await callback.answer("Xizmat topilmadi", show_alert=True)
        return

    lang = user.language if user else "uz"
    title = service.title_uz if lang == "uz" else service.title_ru
    desc = service.description_uz if lang == "uz" else service.description_ru
    price_fmt = f"{service.price:,.0f} so'm".replace(",", " ")

    text = format_service_details_text(title, desc, price_fmt, lang)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=payment_methods_kb(service.id, lang))


@router.callback_query(F.data.startswith("order_service:"))
async def handle_order_service_cta(
    callback: CallbackQuery, session: AsyncSession, user: User | None = None
) -> None:
    """Handle contextual Call-To-Action order buttons (consultation, court, audit)."""
    if not callback.message or not callback.data:
        return

    service_type = callback.data.split(":")[1]
    service = await PaymentService.get_service_by_type(session, service_type)
    lang = user.language if user else "uz"

    if service:
        title = service.title_uz if lang == "uz" else service.title_ru
        desc = service.description_uz if lang == "uz" else service.description_ru
        price_fmt = f"{service.price:,.0f} so'm".replace(",", " ")
        text = format_service_details_text(title, desc, price_fmt, lang)
        await callback.answer()
        if isinstance(callback.message, Message):
            await callback.message.answer(text, reply_markup=payment_methods_kb(service.id, lang))
    else:
        # Fallback to direct lawyer contact if matching service not found
        await handle_contact_lawyer(callback, user)


@router.callback_query(F.data.startswith("pay_p2p:"))
async def handle_p2p_payment(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    user: User | None = None,
) -> None:
    """Provide safe P2P card transfer details and record pending transaction."""
    if not callback.message or not callback.data or not user:
        return

    service_id = int(callback.data.split(":")[1])
    service = await PaymentService.get_service_by_id(session, service_id)
    if not service:
        return

    # Create pending transaction in ledger
    tx = await PaymentService.create_transaction(
        session=session,
        user=user,
        amount=service.price,
        payment_method="p2p_card",
    )

    lang = user.language
    price_fmt = f"{service.price:,.0f} so'm".replace(",", " ")

    # Notify admin / lawyer about new pending transaction
    notify_chat = settings.ADMIN_GROUP_ID or settings.LAWYER_TELEGRAM_ID
    if notify_chat:
        _p2p_name = user.full_name or "Noma'lum"
        _p2p_phone = user.phone_number or "Kiritilmagan"
        alert = (
            "💼 <b>YANGI XIZMAT BUYURTMASI (P2P Karta)</b>\n\n"
            f"👤 <b>Mijoz:</b> {_p2p_name}\n"
            f"📱 <b>Telefon:</b> {_p2p_phone}\n"
            f"💼 <b>Xizmat:</b> {service.title_uz}\n"
            f"💵 <b>Summa:</b> {price_fmt}\n"
            f"🔢 <b>Tranzaksiya:</b> #{tx.id}\n\n"
            "👉 Mijoz to'lov chekini yuborganida tasdiqlang."
        )
        try:
            await bot.send_message(chat_id=notify_chat, text=alert)
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not notify admin about transaction #%d: %s", tx.id, e)

    p2p_text = (
        f"💳 <b>Karta orqali to'lov (Tranzaksiya #{tx.id})</b>\n\n"
        f"💼 Xizmat: <b>{service.title_uz}</b>\n"
        f"💵 To'lov summasi: <b>{price_fmt}</b>\n\n"
        "💳 Karta raqami: <code>9860 0001 2345 6789</code>\n"
        "👤 Qabul qiluvchi: <b>Advokatlik Byurosi</b>\n\n"
        "<i>To'lovni amalga oshirgach, to'lov cheki (skrinshot yoki PDF)ni ushbu bot chatiga yuboring. "
        "Advokat to'lovni tasdiqlashi bilan xizmat ijrosi boshlanadi.</i>"
        if lang == "uz"
        else f"💳 <b>Оплата по карте (Транзакция #{tx.id})</b>\n\n"
        f"💼 Услуга: <b>{service.title_ru}</b>\n"
        f"💵 Сумма к оплате: <b>{price_fmt}</b>\n\n"
        "💳 Номер карты: <code>9860 0001 2345 6789</code>\n"
        "👤 Получатель: <b>Адвокатское Бюро</b>\n\n"
        "<i>После оплаты отправьте квитанцию или чек в этот чат. "
        "После подтверждения адвокатом оказание услуги начнется незамедлительно.</i>"
    )
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(p2p_text)


@router.callback_query(F.data.startswith("pay_stars:"))
async def handle_stars_payment(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    user: User | None = None,
) -> None:
    """Handle Telegram Stars invoice order request safely."""
    if not callback.message or not callback.data or not user:
        return

    service_id = int(callback.data.split(":")[1])
    service = await PaymentService.get_service_by_id(session, service_id)
    if not service:
        return

    tx = await PaymentService.create_transaction(
        session=session,
        user=user,
        amount=service.price,
        payment_method="stars",
    )

    lang = user.language
    price_fmt = f"{service.price:,.0f} so'm".replace(",", " ")

    # Notify admin / lawyer about Stars invoice request
    notify_chat = settings.ADMIN_GROUP_ID or settings.LAWYER_TELEGRAM_ID
    if notify_chat:
        _stars_name = user.full_name or "Noma'lum"
        _stars_phone = user.phone_number or "Kiritilmagan"
        alert = (
            "⭐ <b>YANGI BUYURTMA (Telegram Stars)</b>\n\n"
            f"👤 <b>Mijoz:</b> {_stars_name}\n"
            f"📱 <b>Telefon:</b> {_stars_phone}\n"
            f"💼 <b>Xizmat:</b> {service.title_uz}\n"
            f"💵 <b>Summa:</b> {price_fmt}\n"
            f"🔢 <b>Tranzaksiya:</b> #{tx.id}"
        )
        try:
            await bot.send_message(chat_id=notify_chat, text=alert)
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not notify admin about Stars transaction #%d: %s", tx.id, e)

    stars_text = (
        f"⭐ <b>Telegram Stars orqali buyurtma (Tranzaksiya #{tx.id})</b>\n\n"
        f"💼 Xizmat: <b>{service.title_uz}</b>\n"
        f"💵 Narxi: <b>{price_fmt}</b>\n\n"
        "Telegram Stars orqali individual hisob-faktura (invoys) olish uchun "
        "advokat bilan bog'laning yoki advokatning javobini kuting."
        if lang == "uz"
        else f"⭐ <b>Заказ через Telegram Stars (Транзакция #{tx.id})</b>\n\n"
        f"💼 Услуга: <b>{service.title_ru}</b>\n"
        f"💵 Стоимость: <b>{price_fmt}</b>\n\n"
        "Для выставления индивидуального счета в Telegram Stars свяжитесь с адвокатом "
        "или ожидайте сообщения от специалиста."
    )
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(stars_text)


@router.callback_query(F.data == "contact_lawyer")
async def handle_contact_lawyer(callback: CallbackQuery, user: User | None = None) -> None:
    """Provide lawyer direct contact information."""
    if not callback.message:
        return

    lang = user.language if user else "uz"
    text = (
        "👤 <b>Advokat bilan to'g'ridan-to'g'ri aloqa:</b>\n\n"
        "📞 Telefon: +998 (71) 200-00-00\n"
        "🏢 Manzil: Toshkent sh., Chilonzor tumani, Bunyodkor shoh ko'chasi, 15-uy\n"
        "⏰ Ish vaqti: Dushanba — Shanba, 09:00 dan 18:00 gacha\n\n"
        "<i>Shoshilinch vaziyatlarda Favqulodda SOS bo'limidan foydalaning.</i>"
        if lang == "uz"
        else "👤 <b>Прямой контакт с адвокатом:</b>\n\n"
        "📞 Телефон: +998 (71) 200-00-00\n"
        "🏢 Адрес: г. Ташкент, Чиланзарский р-н, пр-т Бунёдкор, 15\n"
        "⏰ График: Понедельник — Суббота, с 09:00 до 18:00\n\n"
        "<i>В экстренных случаях используйте кнопку SOS.</i>"
    )
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(text)
