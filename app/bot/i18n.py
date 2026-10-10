"""Lightweight i18n translation registry for bot messages."""

from typing import Any

# Central translation map: key -> {"uz": ..., "ru": ...}
_TRANSLATIONS: dict[str, dict[str, str]] = {
    # Inquiry flow
    "phone_required": {
        "uz": (
            "Savolingizga javob berishdan oldin, advokat bilan uzluksiz aloqa uchun "
            "iltimos, telefon raqamingizni yuboring:"
        ),
        "ru": "Перед консультацией, пожалуйста, отправьте ваш номер телефона:",
    },
    "phone_required_button": {
        "uz": (
            "Savol yo'llashdan oldin, advokat bilan aloqa uchun "
            "iltimos, telefon raqamingizni yuboring:"
        ),
        "ru": "Перед отправкой вопроса, пожалуйста, отправьте номер телефона:",
    },
    "phone_required_voice": {
        "uz": "Ovozli xabarni tahlil qilish uchun, iltimos, telefon raqamingizni tasdiqlang:",
        "ru": "Для анализа голосового сообщения, пожалуйста, отправьте номер телефона:",
    },
    "balance_exhausted": {
        "uz": (
            "Hurmatli mijoz, bepul savollar balansingiz yakunlandi.\n"
            "Advokat bilan shaxsiy konsultatsiya olishingiz yoki do'stlarni taklif qilib (+1 savol) olishingiz mumkin."
        ),
        "ru": "Лимит бесплатных консультаций исчерпан. Запишитесь на консультацию или пригласите друзей (+1 вопрос).",
    },
    "balance_exhausted_voice": {
        "uz": (
            "Hurmatli mijoz, bepul savollar balansingiz yakunlandi.\n"
            "Advokat bilan to'liq maslahatlashish uchun xizmat turini tanlang."
        ),
        "ru": "Лимит бесплатных консультаций исчерпан. Выберите подходящую услугу.",
    },
    "inquiry_invite": {
        "uz": (
            "💬 <b>Yuridik savol berish</b>\n\n"
            "Savolingizni matn yoki ovozli xabar ko'rinishida yozib qoldiring. "
            "Advokat masalani o'rganib, qisqa va aniq huquqiy xulosa beradi."
        ),
        "ru": (
            "💬 <b>Задать правовой вопрос</b>\n\n"
            "Отправьте ваш вопрос текстом или голосовым сообщением. "
            "Адвокат предоставит краткий и точный правовой ответ."
        ),
    },
    "greeting_reply": {
        "uz": "Savolingizni batafsil yozib qoldiring",
        "ru": "Пожалуйста, опишите ваш вопрос более подробно.",
    },
    "too_short": {
        "uz": "Savolingizni batafsil yozib qoldiring",
        "ru": "Пожалуйста, опишите ваш вопрос более подробно.",
    },
    "error_text_inquiry": {
        "uz": (
            "Savolingiz qabul qilindi. Hozirda advokat ma'lumotlarni tahlil qilmoqda, "
            "birozdan so'ng to'liq javob yetkaziladi."
        ),
        "ru": "Ваш вопрос принят. Адвокат изучает материалы, ответ будет предоставлен в ближайшее время.",
    },
    "error_voice_inquiry": {
        "uz": (
            "Ovozli xabarni eshitishda texnik xatolik yuz berdi. "
            "Iltimos, savolingizni matn ko'rinishida yozib ko'ring."
        ),
        "ru": "Ошибка обработки голосового сообщения. Пожалуйста, отправьте вопрос текстом.",
    },
    "photo_receipt": {
        "uz": (
            "✅ <b>Rasm qabul qilindi.</b>\n\n"
            "Agar bu to'lov cheki bo'lsa, huquqshunoslar tomonidan tekshirilgach sizga tez orada xabar beramiz. "
            "Yordam kerak bo'lsa, savolingizni yozma yuboring."
        ),
        "ru": (
            "✅ <b>Фотография получена.</b>\n\n"
            "Если это квитанция об оплате, мы уведомим вас после проверки юристами. "
            "Если нужна помощь, отправьте свой вопрос текстом."
        ),
    },
    "voice_transcript_prefix": {
        "uz": "(Ovozli xabaringiz matni: \"{transcript}...\")",
        "ru": "(Текст вашего сообщения: \"{transcript}...\")",
    },
}


def t(key: str, lang: str = "uz", **kwargs: Any) -> str:
    """Look up a translation by key and language, with optional format kwargs."""
    entry = _TRANSLATIONS.get(key)
    if not entry:
        return key
    text = entry.get(lang, entry.get("uz", key))
    if kwargs:
        text = text.format(**kwargs)
    return text
