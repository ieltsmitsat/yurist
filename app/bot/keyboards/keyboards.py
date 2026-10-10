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
    """Contextual Call-to-Action inline buttons attached to AI legal responses."""
    if cta_type in ("none", ""):
        return None

    buttons = []
    if cta_type == "audit":
        btn_text = (
            "📑 To'liq shartnoma auditiga buyurtma"
            if lang == "uz"
            else "📑 Заказать полный аудит договора"
        )
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data="order_service:audit")])
    elif cta_type == "court":
        btn_text = "⚖️ Sudda advokat vakilligi" if lang == "uz" else "⚖️ Представительство в суде"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data="order_service:court")])
    else:
        btn_text = (
            "📞 Shaxsiy konsultatsiyaga yozilish"
            if lang == "uz"
            else "📞 Записаться на личную консультацию"
        )
        buttons.append(
            [InlineKeyboardButton(text=btn_text, callback_data="order_service:consultation")]
        )

    # Referral / Invite friends option (+1 free question)
    ref_btn_text = (
        "👥 Do'stlarni taklif qilish (+1 savol)"
        if lang == "uz"
        else "👥 Пригласить друзей (+1 вопрос)"
    )
    buttons.append([InlineKeyboardButton(text=ref_btn_text, callback_data="show_referral")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
                    text="📞 Advokatni chaqirish (Tezkor)", callback_data="sos_call_lawyer"
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
                    text="📞 Вызов адвоката (Срочно)", callback_data="sos_call_lawyer"
                )
            ],
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def services_catalog_kb(services: Sequence[Service], lang: str = "uz") -> InlineKeyboardMarkup:
    """Inline catalog of active legal services."""
    buttons = []
    for s in services:
        title = s.title_uz if lang == "uz" else s.title_ru
        price_fmt = f"{s.price:,.0f} so'm".replace(",", " ")
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{title} — {price_fmt}", callback_data=f"buy_service:{s.id}"
                )
            ]
        )
    contact_text = (
        "👤 Advokat bilan to'g'ridan-to'g'ri bog'lanish"
        if lang == "uz"
        else "👤 Прямой контакт с адвокатом"
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
                    text="👤 Advokat bilan bog'lanish va buyurtma berish",
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
                    text="👤 Связаться с адвокатом для заказа",
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
        "Assalomu alaykum! Malakali advokat va AI yurist yordamchisi. Savolingizni bepul bering:"
        if lang == "uz"
        else "Здравствуйте! Квалифицированный адвокат и AI-помощник. Задайте свой правовой вопрос бесплатно:"
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

