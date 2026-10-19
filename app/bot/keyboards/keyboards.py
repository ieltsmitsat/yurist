"""Keyboards (Reply and Inline) for bilingual Telegram Bot."""

from collections.abc import Sequence
from urllib.parse import quote

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from app.db.models.service import Service


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def language_selection_kb() -> InlineKeyboardMarkup:
    """Language selection keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="set_lang:uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru"),
            ]
        ]
    )


def phone_request_kb(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Phone number request keyboard (Hard Gate)."""
    btn_text = "📱 Telefon raqamni yuborish" if lang == "uz" else "📱 Отправить номер телефона"
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=btn_text, request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_kb(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Main menu keyboard."""
    if lang == "uz":
        keyboard = [
            [
                KeyboardButton(text="💬 Yuridik savol berish"),
                KeyboardButton(text="📑 Hujjat auditi"),
            ],
            [
                KeyboardButton(text="💼 Xizmatlar va Narxlar"),
                KeyboardButton(text="📞 Ishonch telefon raqamlari"),
            ],
            [
                KeyboardButton(text="👥 Taklif qilish (+1 savol)"),
                KeyboardButton(text="🆘 Favqulodda yordam (SOS)"),
            ],
            [
                KeyboardButton(text="⚙️ Sozlamalar"),
            ]
        ]
    else:
        keyboard = [
            [
                KeyboardButton(text="💬 Задать правовой вопрос"),
                KeyboardButton(text="📑 Аудит документа"),
            ],
            [
                KeyboardButton(text="💼 Услуги и Цены"),
                KeyboardButton(text="📞 Телефоны доверия"),
            ],
            [
                KeyboardButton(text="👥 Пригласить (+1 вопрос)"),
                KeyboardButton(text="🆘 Экстренная помощь (SOS)"),
            ],
            [
                KeyboardButton(text="⚙️ Настройки"),
            ]
        ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def cta_keyboard(cta_type: str, lang: str = "uz") -> InlineKeyboardMarkup | None:
    """Contextual Call-to-Action inline buttons attached to AI legal responses.

    Dynamically adapts the 1st button to match the user's question:
    - audit: Shartnoma auditi va ekspertiza
    - claim: Da'vo arizasi va talabnoma tuzish
    - court: Sudda huquqshunos vakilligi
    - business: Biznes uchun yuridik hamrohlik
    - consultation: Shaxsiy konsultatsiyaga yozilish
    """
    if cta_type in ("none", ""):
        return None

    buttons = []
    if cta_type == "audit":
        btn_text = (
            "📑 Shartnoma auditiga buyurtma"
            if lang == "uz"
            else "📑 Заказать аудит договора"
        )
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data="order_service:audit")])
    elif cta_type == "claim":
        btn_text = (
            "📝 Da'vo arizasi / talabnoma tuzish"
            if lang == "uz"
            else "📝 Составление иска и претензии"
        )
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data="order_service:claim")])
    elif cta_type == "court":
        btn_text = (
            "⚖️ Sudda huquqshunos vakilligi"
            if lang == "uz"
            else "⚖️ Представительство в суде"
        )
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data="order_service:court")])
    elif cta_type == "business":
        btn_text = (
            "🏢 Biznes uchun yuridik xizmat"
            if lang == "uz"
            else "🏢 Юридическое обслуживание бизнеса"
        )
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data="order_service:business")])
    else:
        btn_text = (
            "📞 Shaxsiy konsultatsiyaga yozilish"
            if lang == "uz"
            else "📞 Записаться на личную консультацию"
        )
        buttons.append(
            [InlineKeyboardButton(text=btn_text, callback_data="order_service:consultation")]
        )

    # Second button: Do'stlarni taklif qilish (+1 savol)
    ref_btn_text = (
        "👥 Do'stlarni taklif qilish (+1 savol)"
        if lang == "uz"
        else "👥 Пригласить друзей (+1 вопрос)"
    )
    buttons.append([InlineKeyboardButton(text=ref_btn_text, callback_data="show_referral")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def service_fulfillment_kb(
    tx_id: int | None,
    ref_link: str,
    lang: str = "uz",
) -> InlineKeyboardMarkup:
    """Rating (1-5 stars) and viral sharing keyboard sent to client upon service completion."""
    tx_param = f"tx_{tx_id}" if tx_id else "direct"
    stars_row = [
        InlineKeyboardButton(text=f"⭐ {i}", callback_data=f"rate_srv:{tx_param}_{i}")
        for i in range(1, 6)
    ]

    share_text = (
        "Assalomu alaykum! Men ushbu bot orqali malakali yurist va advokat xizmatidan foydalandim va bu bot judayam foydali ekan. Siz ham ushbu botdan foydalanib ko’ring."
        if lang == "uz"
        else "Здравствуйте! Я воспользовался услугами квалифицированного юриста и адвоката через этого бота, и этот бот оказался очень полезным. Попробуйте и вы воспользоваться им."
    )
    share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={quote(share_text)}"
    share_btn_text = "📢 Yaqinlarga ulashish" if lang == "uz" else "📢 Поделиться с близкими"
    new_srv_text = "💼 Boshqa xizmatlar" if lang == "uz" else "💼 Другие услуги"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            stars_row,
            [InlineKeyboardButton(text=share_btn_text, url=share_url)],
            [InlineKeyboardButton(text=new_srv_text, callback_data="back_to_services")],
        ]
    )


def service_rated_kb(ref_link: str, lang: str = "uz") -> InlineKeyboardMarkup:
    """Follow-up keyboard after client submitted their star rating."""
    share_text = (
        "Assalomu alaykum! Men ushbu bot orqali malakali yurist va advokat xizmatidan foydalandim va bu bot judayam foydali ekan. Siz ham ushbu botdan foydalanib ko’ring."
        if lang == "uz"
        else "Здравствуйте! Я воспользовался услугами квалифицированного юриста и адвоката через этого бота, и этот бот оказался очень полезным. Попробуйте и вы воспользоваться им."
    )
    share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={quote(share_text)}"
    share_btn_text = "📢 Yaqinlarga ulashish" if lang == "uz" else "📢 Поделиться с близкими"
    new_srv_text = "💼 Boshqa xizmatlar" if lang == "uz" else "💼 Другие услуги"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=share_btn_text, url=share_url)],
            [InlineKeyboardButton(text=new_srv_text, callback_data="back_to_services")],
        ]
    )


def sos_options_kb(lang: str = "uz") -> InlineKeyboardMarkup:
    """SOS Emergency Hotline options keyboard."""
    if lang == "uz":
        buttons = [
            [
                InlineKeyboardButton(
                    text="🚨 IIB to'xtatganda (3 ta qoida)", callback_data="sos_guide:police"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏢 Tintuv va tekshiruvlar (Ko'rsatma)", callback_data="sos_guide:raid"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📞 Huquqshunosni chaqirish (Tezkor)", callback_data="sos_call_lawyer"
                )
            ],
        ]
    else:
        buttons = [
            [
                InlineKeyboardButton(
                    text="🚨 Остановка полицией (3 правила)", callback_data="sos_guide:police"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏢 Обыск и проверка бизнеса (Инструкция)", callback_data="sos_guide:raid"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📞 Вызов юриста (Срочно)", callback_data="sos_call_lawyer"
                )
            ],
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def services_catalog_kb(services: Sequence[Service], lang: str = "uz") -> InlineKeyboardMarkup:
    """Inline catalog of active legal services."""
    from app.services.payment_service import PaymentService

    buttons = []
    for s in services:
        title = s.title_uz if lang == "uz" else s.title_ru
        price_fmt = PaymentService.format_service_price(s.price)
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{title} — {price_fmt}", callback_data=f"buy_service:{s.id}"
                )
            ]
        )
    contact_text = (
        "👤 Huquqshunos bilan to'g'ridan-to'g'ri bog'lanish"
        if lang == "uz"
        else "👤 Прямой контакт с юристом"
    )
    buttons.append([InlineKeyboardButton(text=contact_text, callback_data="contact_lawyer")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_methods_kb(service_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    """Safe payment and booking options for selected service."""
    if lang == "uz":
        buttons = [
            [
                InlineKeyboardButton(
                    text="💳 Karta orqali to'lov (P2P)", callback_data=f"pay_p2p:{service_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Telegram Stars", callback_data=f"pay_stars:{service_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Huquqshunos bilan bog'lanish va buyurtma berish",
                    callback_data="contact_lawyer",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Xizmatlar ro'yxatiga qaytish", callback_data="back_to_services"
                )
            ],
        ]
    else:
        buttons = [
            [
                InlineKeyboardButton(
                    text="💳 Оплата картой (P2P)", callback_data=f"pay_p2p:{service_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Telegram Stars", callback_data=f"pay_stars:{service_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Связаться с юристом для заказа",
                    callback_data="contact_lawyer",
                )
            ],
            [InlineKeyboardButton(text="🔙 К списку услуг", callback_data="back_to_services")],
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def settings_kb(lang: str = "uz") -> InlineKeyboardMarkup:
    """Settings menu inline keyboard."""
    btn_text = "🌐 Tilni o'zgartirish" if lang == "uz" else "🌐 Сменить язык"
    ref_text = "👥 Do'stlarni taklif qilish" if lang == "uz" else "👥 Пригласить друзей"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=btn_text, callback_data="settings:change_lang")],
            [InlineKeyboardButton(text=ref_text, callback_data="settings:show_referral")],
        ]
    )


def referral_share_kb(ref_link: str, lang: str = "uz") -> InlineKeyboardMarkup:
    """Inline keyboard for viral referral sharing (1-click Telegram share) and live stats refresh."""
    share_text = (
        "Assalomu alaykum! Men ushbu bot orqali malakali yurist va advokat xizmatidan foydalandim va bu bot judayam foydali ekan. Siz ham ushbu botdan foydalanib ko’ring."
        if lang == "uz"
        else "Здравствуйте! Я воспользовался услугами квалифицированного юриста и адвоката через этого бота, и этот бот оказался очень полезным. Попробуйте и вы воспользоваться им."
    )
    share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={quote(share_text)}"
    share_btn_text = "📤 Do'stlarga ulashish" if lang == "uz" else "📤 Поделиться с друзьями"
    refresh_btn_text = "🔄 Yangilash" if lang == "uz" else "🔄 Обновить"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=share_btn_text, url=share_url)],
            [InlineKeyboardButton(text=refresh_btn_text, callback_data="refresh_referral")],
        ]
    )


def helplines_categories_reply_kb(
    categories: list[tuple[str, str]], lang: str = "uz"
) -> ReplyKeyboardMarkup:
    """Generate reply keyboard for helpline categories with a back button."""
    keyboard: list[list[KeyboardButton]] = []
    
    # 2 buttons per row or 1 if long
    row: list[KeyboardButton] = []
    for cat_uz, cat_ru in categories:
        name = cat_uz if lang == "uz" else cat_ru
        btn_text = f"📂 {name}"
        row.append(KeyboardButton(text=btn_text))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Add back to main menu button
    back_text = "🔙 Asosiy menyuga qaytish" if lang == "uz" else "🔙 Главное меню"
    keyboard.append([KeyboardButton(text=back_text)])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


