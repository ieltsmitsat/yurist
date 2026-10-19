"""Services catalog and payment ledger handlers (Off-limits rule safe)."""

import logging
from typing import Any

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.keyboards import (
    payment_methods_kb,
    service_fulfillment_kb,
    service_rated_kb,
    services_catalog_kb,
)
from app.core.config import settings
from app.db.models.user import User
from app.services.payment_service import PaymentService
from app.services.referral_service import ReferralService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router(name="services_router")
router.message.filter(F.chat.type == "private")


def format_service_details_text(service_title: str, service_desc: str | None, price_fmt: str, lang: str) -> str:
    """Format structured legal service card with deliverables and pricing."""
    if lang == "uz":
        return (
            f"💼 <b>{service_title}</b>\n\n"
            f"{service_desc or 'Professional yuridik xizmat.'}\n\n"
            f"💵 <b>Rasmiy narxi:</b> {price_fmt}\n"
            "⏱ <b>Bajarilish muddati:</b> To'lov tasdiqlangach 24 soat ichida (yoki kelishuv asosida).\n\n"
            "<i>Quyidagi to'lov yoki bog'lanish usulini tanlang:</i>"
        )
    return (
        f"💼 <b>{service_title}</b>\n\n"
        f"{service_desc or 'Квалифицированная юридическая помощь.'}\n\n"
        f"💵 <b>Стоимость:</b> {price_fmt}\n"
        "⏱ <b>Срок исполнения:</b> В течение 24 часов после оплаты (или по договоренности).\n\n"
        "<i>Выберите способ оплаты или связи с юристом:</i>"
    )


def is_services_menu_text_trigger(message: Message) -> bool:
    """Detect if client is requesting services catalog via button or text."""
    if not message.text:
        return False
    t = message.text.strip().lower()
    if t in ["💼 xizmatlar va narxlar", "💼 услуги и цены"]:
        return True
    from app.bot.handlers.business.messages import is_general_services_inquiry

    return is_general_services_inquiry(t)


@router.message(is_services_menu_text_trigger)
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
        "Malakali huquqshunoslar tomonidan ko'rsatiladigan professional huquqiy xizmatlar bilan tanishing va o'zingizga keraklisini tanlang:\n\n"
        "✅ Rasmiy yuridik shartnoma\n"
        "✅ 100% maxfiylik va huquqiy himoya\n"
        "✅ Qonuniy asoslangan professional yondashuv"
        if lang == "uz"
        else "💼 <b>Юридические Услуги и Тарифы</b>\n\n"
        "Ознакомьтесь с перечнем профессиональных правовых услуг и выберите нужный тариф:\n\n"
        "✅ Официальный юридический договор\n"
        "✅ 100% конфиденциальность и правовая защита\n"
        "✅ Опытные квалифицированные специалисты"
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
    price_fmt = PaymentService.format_service_price(service.price)

    text = format_service_details_text(title, desc, price_fmt, lang)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=payment_methods_kb(service.id, lang))


@router.callback_query(F.data.startswith("order_service:"))
async def handle_order_service_cta(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User | None = None,
    bot: Bot | None = None,
) -> None:
    """Handle contextual Call-To-Action order buttons (consultation, court, audit, claim, business)."""
    if not callback.message or not callback.data:
        return

    service_type = callback.data.split(":")[1]
    service = await PaymentService.get_service_by_type(session, service_type)
    if not service:
        await PaymentService.seed_default_services(session)
        service = await PaymentService.get_service_by_type(session, service_type)

    lang = user.language if user else "uz"

    if service:
        title = service.title_uz if lang == "uz" else service.title_ru
        desc = service.description_uz if lang == "uz" else service.description_ru
        price_fmt = PaymentService.format_service_price(service.price)
        text = format_service_details_text(title, desc, price_fmt, lang)
        await callback.answer()

        chat = getattr(callback.message, "chat", None)
        chat_type = getattr(chat, "type", "private") if chat else "private"
        if chat_type != "private" and bot is not None:
            try:
                await bot.send_message(
                    chat_id=callback.from_user.id,
                    text=text,
                    reply_markup=payment_methods_kb(service.id, lang),
                )
                await callback.answer(
                    "Xizmat tafsilotlari va to'lov shaxsiy bot chatiga yuborildi! 👇",
                    show_alert=True,
                )
                return
            except Exception:  # noqa: BLE001
                bot_user = await bot.get_me()
                start_url = f"https://t.me/{bot_user.username}?start=order_{service_type}"
                if isinstance(callback.message, Message):
                    await callback.message.reply(
                        f"👉 {title} xizmatiga buyurtma berish uchun botga kiring: {start_url}"
                    )
                return

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

    # Create pending transaction in ledger with service title reference
    tx = await PaymentService.create_transaction(
        session=session,
        user=user,
        amount=service.price,
        payment_method="p2p_card",
        transaction_ref=service.title_uz,
    )

    lang = user.language
    price_fmt = PaymentService.format_service_price(service.price)

    # Notify admin / lawyer about new pending transaction
    notify_chat = settings.ADMIN_GROUP_ID or settings.LAWYER_TELEGRAM_ID
    if notify_chat:
        alert = (
            "💼 <b>YANGI XIZMAT BUYURTMASI (P2P Karta)</b>\n\n"
            f"👤 <b>Mijoz:</b> {user.full_name or 'Noma\'lum'}\n"
            f"📱 <b>Telefon:</b> {user.phone_number or 'Kiritilmagan'}\n"
            f"💼 <b>Xizmat:</b> {service.title_uz}\n"
            f"💵 <b>Summa:</b> {price_fmt}\n"
            f"🔢 <b>Tranzaksiya:</b> #{tx.id}\n\n"
            "👉 Mijoz to'lov chekini yuborganida tasdiqlang."
        )
        try:
            await bot.send_message(chat_id=notify_chat, text=alert)
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not notify admin about transaction #%d: %s", tx.id, e)

    from app.services.org_settings_service import OrgSettingsService
    org_settings = await OrgSettingsService.get_settings(session)
    card_number = org_settings.card_number
    card_holder = org_settings.card_holder

    p2p_text = (
        f"💳 <b>Karta orqali to'lov (Tranzaksiya #{tx.id})</b>\n\n"
        f"💼 Xizmat: <b>{service.title_uz}</b>\n"
        f"💵 To'lov summasi: <b>{price_fmt}</b>\n\n"
        f"💳 Karta raqami: <code>{card_number}</code>\n"
        f"👤 Qabul qiluvchi: <b>{card_holder}</b>\n\n"
        "<i>To'lovni amalga oshirgach, to'lov cheki (skrinshot yoki PDF)ni ushbu bot chatiga yuboring. "
        "Huquqshunos to'lovni tasdiqlashi bilan xizmat ko’rsatish darhol boshlanadi.</i>"
        if lang == "uz"
        else f"💳 <b>Оплата по карте (Транзакция #{tx.id})</b>\n\n"
        f"💼 Услуга: <b>{service.title_ru}</b>\n"
        f"💵 Сумма к оплате: <b>{price_fmt}</b>\n\n"
        f"💳 Номер карты: <code>{card_number}</code>\n"
        f"👤 Получатель: <b>{card_holder}</b>\n\n"
        "<i>После оплаты отправьте квитанцию или чек в этот чат. "
        "После подтверждения юристом оказание услуги начнется незамедлительно.</i>"
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
        transaction_ref=service.title_uz,
    )

    lang = user.language
    price_fmt = PaymentService.format_service_price(service.price)

    # Notify admin / lawyer about Stars invoice request
    notify_chat = settings.ADMIN_GROUP_ID or settings.LAWYER_TELEGRAM_ID
    if notify_chat:
        alert = (
            "⭐ <b>YANGI BUYURTMA (Telegram Stars)</b>\n\n"
            f"👤 <b>Mijoz:</b> {user.full_name or 'Noma\'lum'}\n"
            f"📱 <b>Telefon:</b> {user.phone_number or 'Kiritilmagan'}\n"
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
        "huquqshunos bilan bog'laning yoki huquqshunosning javobini kuting."
        if lang == "uz"
        else f"⭐ <b>Заказ через Telegram Stars (Транзакция #{tx.id})</b>\n\n"
        f"💼 Услуга: <b>{service.title_ru}</b>\n"
        f"💵 Стоимость: <b>{price_fmt}</b>\n\n"
        "Для выставления индивидуального счета в Telegram Stars свяжитесь с юристом "
        "или ожидайте сообщения от специалиста."
    )
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(stars_text)


@router.callback_query(F.data == "contact_lawyer")
async def handle_contact_lawyer(
    callback: CallbackQuery, session: AsyncSession, user: User | None = None
) -> None:
    """Provide lawyer direct contact information from dynamic OrgSettings."""
    if not callback.message:
        return

    from app.services.org_settings_service import OrgSettingsService

    org_settings = await OrgSettingsService.get_settings(session)
    contact_phone = org_settings.contact_phone
    office_address = org_settings.office_address
    working_hours = org_settings.working_hours

    lang = user.language if user else "uz"
    text = (
        "👤 <b>Huquqshunos bilan to'g'ridan-to'g'ri aloqa:</b>\n\n"
        f"📞 Telefon: {contact_phone}\n"
        f"🏢 Manzil: {office_address}\n"
        f"⏰ Ish vaqti: {working_hours}\n\n"
        "<i>Shoshilinch vaziyatlarda Favqulodda SOS bo'limidan foydalaning.</i>"
        if lang == "uz"
        else "👤 <b>Прямой контакт с юристом:</b>\n\n"
        f"📞 Телефон: {contact_phone}\n"
        f"🏢 Адрес: {office_address}\n"
        f"⏰ График: {working_hours}\n\n"
        "<i>В экстренных случаях используйте кнопку SOS.</i>"
    )
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(text)


@router.callback_query(F.data.startswith("pay_ok:"))
async def handle_payment_approval(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Handle lawyer/admin approving payment from the payment topic."""
    if not callback.data:
        return

    admin_name = callback.from_user.full_name if callback.from_user else "Admin"
    raw_payload = callback.data.split("pay_ok:")[1]  # tx_123 or u_456

    target_user: User | None = None
    target_tx: Any = None

    if raw_payload.startswith("tx_"):
        tx_id_str = raw_payload[3:]
        if tx_id_str.isdigit():
            tx_id = int(tx_id_str)
            target_tx = await PaymentService.confirm_payment(
                session=session,
                transaction_id=tx_id,
            )
            if target_tx:
                stmt_u = select(User).where(User.id == target_tx.user_id)
                res_u = await session.execute(stmt_u)
                target_user = res_u.scalar_one_or_none()
    elif raw_payload.startswith("u_"):
        user_id_str = raw_payload[2:]
        if user_id_str.isdigit():
            stmt_u = select(User).where(User.id == int(user_id_str))
            res_u = await session.execute(stmt_u)
            target_user = res_u.scalar_one_or_none()

    # 1. Notify client in private bot chat
    if target_user and target_user.telegram_id:
        user_lang = target_user.language or "uz"
        from app.services.org_settings_service import OrgSettingsService

        org_settings = await OrgSettingsService.get_settings(session)
        service_ref = target_tx.transaction_ref if target_tx else None
        client_msg = OrgSettingsService.format_payment_confirmed_text(
            transaction_ref=service_ref,
            settings_record=org_settings,
            lang=user_lang,
        )
        try:
            if getattr(target_user, "business_connection_id", None):
                await bot.send_message(
                    chat_id=target_user.telegram_id,
                    text=client_msg,
                    business_connection_id=target_user.business_connection_id,
                )
            else:
                await bot.send_message(chat_id=target_user.telegram_id, text=client_msg)
        except Exception:  # noqa: BLE001
            try:
                await bot.send_message(chat_id=target_user.telegram_id, text=client_msg)
            except Exception as e:  # noqa: BLE001
                logger.warning("Could not send payment confirmation to user %s: %s", target_user.telegram_id, e)

    # 2. Update message in group topic with "Ish bajarildi" button
    await callback.answer("To'lov tasdiqlandi! Mijozga xabar yetkazildi.", show_alert=True)
    if isinstance(callback.message, Message):
        status_note = (
            f"\n\n✅ <b>TO'LOV TASDIQLANDI</b> (Mas'ul: {admin_name})\n"
            "<i>Mijozga tasdiqnoma yetkazildi. Xizmat ko'rsatib bo'lingach, quyidagi «Ish bajarildi» tugmasini bosing:</i>"
        )
        done_payload = (
            f"pay_done:tx_{target_tx.id}"
            if target_tx
            else f"pay_done:u_{target_user.id if target_user else 0}"
        )
        done_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🏁 Ish bajarildi (Mijozga yetkazish)",
                        callback_data=done_payload,
                    )
                ]
            ]
        )
        if callback.message.caption:
            await callback.message.edit_caption(
                caption=callback.message.caption + status_note,
                reply_markup=done_kb,
            )
        elif callback.message.text:
            await callback.message.edit_text(
                text=callback.message.text + status_note,
                reply_markup=done_kb,
            )


@router.callback_query(F.data.startswith("pay_done:"))
async def handle_service_completed(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Handle lawyer/admin marking service as completed from the payment topic."""
    if not callback.data:
        return

    admin_name = callback.from_user.full_name if callback.from_user else "Huquqshunos"
    raw_payload = callback.data.split("pay_done:")[1]  # tx_123 or u_456

    target_user: User | None = None
    target_tx: Any = None
    tx_id: int | None = None

    if raw_payload.startswith("tx_"):
        tx_id_str = raw_payload[3:]
        if tx_id_str.isdigit():
            from app.db.models.transaction import Transaction

            tx_id = int(tx_id_str)
            stmt = select(Transaction).where(Transaction.id == tx_id)
            res = await session.execute(stmt)
            target_tx = res.scalar_one_or_none()
            if target_tx:
                target_tx.payment_status = "fulfilled"
                await session.commit()
                stmt_u = select(User).where(User.id == target_tx.user_id)
                res_u = await session.execute(stmt_u)
                target_user = res_u.scalar_one_or_none()
    elif raw_payload.startswith("u_"):
        user_id_str = raw_payload[2:]
        if user_id_str.isdigit():
            stmt_u = select(User).where(User.id == int(user_id_str))
            res_u = await session.execute(stmt_u)
            target_user = res_u.scalar_one_or_none()

    # 1. Notify client with Completion + Rating (1-5 stars) + Share with friends button
    if target_user and target_user.telegram_id:
        user_lang = target_user.language or "uz"
        bot_user = await bot.get_me()
        bot_username = bot_user.username or settings.BOT_USERNAME
        ref_link = ReferralService.get_referral_link(bot_username, target_user)

        completion_text = (
            "🎉 <b>Hurmatli mijoz!</b>\n\n"
            "Siz buyurtma qilgan yuridik xizmat muvaffaqiyatli bajarildi va yakunlandi!\n\n"
            "Biz uchun sizning fikringiz juda muhim. Iltimos, ko'rsatilgan xizmat sifatini baholang:"
            if user_lang == "uz"
            else "🎉 <b>Уважаемый клиент!</b>\n\n"
            "Юридическая услуга успешно выполнена в полном объеме!\n\n"
            "Нам очень важно ваше мнение. Пожалуйста, оцените качество оказанной услуги:"
        )

        kb = service_fulfillment_kb(tx_id=tx_id, ref_link=ref_link, lang=user_lang)
        try:
            if getattr(target_user, "business_connection_id", None):
                await bot.send_message(
                    chat_id=target_user.telegram_id,
                    text=completion_text,
                    reply_markup=kb,
                    business_connection_id=target_user.business_connection_id,
                )
            else:
                await bot.send_message(
                    chat_id=target_user.telegram_id,
                    text=completion_text,
                    reply_markup=kb,
                )
        except Exception:  # noqa: BLE001
            try:
                await bot.send_message(
                    chat_id=target_user.telegram_id,
                    text=completion_text,
                    reply_markup=kb,
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("Could not send service fulfillment to user %s: %s", target_user.telegram_id, e)

    # 2. Update topic message to completed state without buttons
    await callback.answer("Xizmat bajarildi deb belgilandi! Mijozga baholash yuborildi.", show_alert=True)
    if isinstance(callback.message, Message):
        done_badge = (
            f"\n\n🏁 <b>XIZMAT TO'LIQ BAJARILDI</b> (Mas'ul: {admin_name})\n"
            "<i>Mijozga xizmat yakunlangani, sifatni baholash va ulashish taklifi yetkazildi.</i>"
        )
        if callback.message.caption:
            await callback.message.edit_caption(
                caption=callback.message.caption + done_badge,
                reply_markup=None,
            )
        elif callback.message.text:
            await callback.message.edit_text(
                text=callback.message.text + done_badge,
                reply_markup=None,
            )


@router.callback_query(F.data.startswith("rate_srv:"))
async def handle_rate_service(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    user: User | None = None,
) -> None:
    """Handle client rating the completed service (1-5 stars)."""
    if not callback.data or not callback.message:
        return

    # Payload: rate_srv:tx_<id>_<stars> or rate_srv:direct_<stars>
    parts = callback.data.split("rate_srv:")[1].split("_")
    stars_str = parts[-1]
    stars = int(stars_str) if stars_str.isdigit() else 5

    current_user = user or (
        await UserService.get_by_telegram_id(session, callback.from_user.id)
        if callback.from_user
        else None
    )
    lang = current_user.language if current_user else "uz"

    bot_user = await bot.get_me()
    bot_username = bot_user.username or settings.BOT_USERNAME
    ref_link = (
        ReferralService.get_referral_link(bot_username, current_user)
        if current_user
        else f"https://t.me/{bot_username}"
    )

    stars_display = "⭐️" * stars
    thank_text = (
        f"{stars_display}\n\n"
        "<b>Katta rahmat!</b> Bahoingiz qabul qilindi.\n"
        "Sizning fikringiz xizmatlarimiz sifatini yanada oshirishga yordam beradi.\n\n"
        "Agar xizmatimiz ma'qul kelgan bo'lsa, uni yaqinlaringizga ham ulashing:"
        if lang == "uz"
        else f"{stars_display}\n\n"
        "<b>Большое спасибо!</b> Ваша оценка принята.\n"
        "Ваш отзыв помогает нам становиться лучше.\n\n"
        "Если вы остались довольны, поделитесь ботом со своими близкими:"
    )

    await callback.answer(f"Rahmat! {stars} ball bilan baholadingiz.")
    if isinstance(callback.message, Message):
        await callback.message.edit_text(thank_text, reply_markup=service_rated_kb(ref_link, lang))


@router.callback_query(F.data.startswith("pay_cancel:"))
async def handle_payment_rejection(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Handle lawyer/admin rejecting payment from the payment topic."""
    if not callback.data:
        return

    admin_name = callback.from_user.full_name if callback.from_user else "Admin"
    raw_payload = callback.data.split("pay_cancel:")[1]  # tx_123 or u_456

    target_user: User | None = None
    target_tx: Any = None

    if raw_payload.startswith("tx_"):
        tx_id_str = raw_payload[3:]
        if tx_id_str.isdigit():
            from app.db.models.transaction import Transaction
            tx_id = int(tx_id_str)
            stmt = select(Transaction).where(Transaction.id == tx_id)
            res = await session.execute(stmt)
            target_tx = res.scalar_one_or_none()
            if target_tx:
                target_tx.payment_status = "failed"
                await session.commit()
                stmt_u = select(User).where(User.id == target_tx.user_id)
                res_u = await session.execute(stmt_u)
                target_user = res_u.scalar_one_or_none()
    elif raw_payload.startswith("u_"):
        user_id_str = raw_payload[2:]
        if user_id_str.isdigit():
            stmt_u = select(User).where(User.id == int(user_id_str))
            res_u = await session.execute(stmt_u)
            target_user = res_u.scalar_one_or_none()

    # 1. Notify client in private bot chat about issue
    if target_user and target_user.telegram_id:
        user_lang = target_user.language or "uz"
        client_msg = (
            "⚠️ <b>To'lovni tekshirishda muammo yuzaga keldi</b>\n\n"
            "Siz yuborgan to'lov cheki yoki ma'lumotlarida noaniqlik aniqlandi va to'lov tasdiqlanmadi.\n\n"
            "Iltimos, to'lov muvaffaqiyatli o'tganligini tekshirib, chek skrinshotini qaytadan yuboring "
            "yoki yordam uchun huquqshunos bilan bog'laning."
            if user_lang == "uz"
            else "⚠️ <b>Возникла проблема при проверке платежа</b>\n\n"
            "В отправленном чеке или реквизитах обнаружена неточность, платеж не подтвержден.\n\n"
            "Пожалуйста, проверьте списание средств и отправьте квитанцию повторно "
            "либо свяжитесь с юристом."
        )
        try:
            if getattr(target_user, "business_connection_id", None):
                await bot.send_message(
                    chat_id=target_user.telegram_id,
                    text=client_msg,
                    business_connection_id=target_user.business_connection_id,
                )
            else:
                await bot.send_message(chat_id=target_user.telegram_id, text=client_msg)
        except Exception:  # noqa: BLE001
            try:
                await bot.send_message(chat_id=target_user.telegram_id, text=client_msg)
            except Exception as e:  # noqa: BLE001
                logger.warning("Could not send payment rejection to user %s: %s", target_user.telegram_id, e)

    # 2. Update message in group topic (remove buttons and show rejected badge)
    await callback.answer("To'lov bekor qilindi. Mijozga xabar yetkazildi.", show_alert=True)
    if isinstance(callback.message, Message):
        status_note = f"\n\n❌ <b>TO'LOV BEKOR QILINDI</b> (Mas'ul: {admin_name})\n<i>Mijozga qayta urinish bo'yicha xabar yuborildi.</i>"
        if callback.message.caption:
            await callback.message.edit_caption(
                caption=callback.message.caption + status_note,
                reply_markup=None,
            )
        elif callback.message.text:
            await callback.message.edit_text(
                text=callback.message.text + status_note,
                reply_markup=None,
            )

