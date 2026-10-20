import asyncio
import logging
import re
from collections.abc import Sequence

from aiogram import Bot, Router
from aiogram.types import BusinessConnection, Message
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import BusinessPauseManager
from app.db.models.inquiry import Inquiry
from app.db.models.service import Service
from app.db.models.transaction import Transaction
from app.services.ai.llm_client import LLMService
from app.services.chat_service import ChatService
from app.services.group_notification_service import GroupNotificationService
from app.services.org_settings_service import OrgSettingsService
from app.services.payment_service import PaymentService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router(name="business_router")
llm_service = LLMService()

PHONE_REGEX = re.compile(
    r"(?:\+?998[\s-]?)?(?:9[01345789]|33|77|88|50|95)[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b"
)


def extract_phone(text: str) -> str | None:
    """Extract and normalize Uzbekistan phone number from text."""
    match = PHONE_REGEX.search(text)
    if not match:
        return None
    raw = re.sub(r"[^\d+]", "", match.group(0))
    if not raw.startswith("+"):
        if raw.startswith("998"):
            raw = "+" + raw
        elif len(raw) == 9:
            raw = "+998" + raw
    return raw


def is_personal_identity_inquiry(text: str) -> bool:
    """Check if the user is asking about the lawyer's personal identity, age, background, or personal life."""
    q = text.lower().strip()
    clean_no_punct = re.sub(r"[^\w\s]", " ", q)
    words = clean_no_punct.split()

    if not words:
        return False

    direct_patterns = [
        # Identity / Name
        "kimsiz",
        "kimsan",
        "kim bu",
        "kim siz",
        "kim san",
        "kim u",
        "ismingiz nima",
        "ismingiz",
        "isming nima",
        "isming",
        "ismiz",
        "familiyangiz",
        "familiya",
        "otangiz",
        "sharifingiz",
        "o'zingiz haqingizda",
        "ozingiz haqingizda",
        "o'zingiz haqingizda gapiring",
        "ozingiz haqingizda gapiring",
        "o'zingiz haqingizda ma'lumot",
        "ozingiz haqingizda malumot",
        "haqingizda gapiring",
        "haqingizda malumot",
        "haqingizda ma'lumot",
        "tarjimai hol",
        "biografiya",
        # Age / Birth year
        "necha yosh",
        "nechchi yosh",
        "nechi yosh",
        "necha yoshsiz",
        "nechchi yoshsiz",
        "nechi yoshsiz",
        "necha yoshdasiz",
        "necha yoshdasan",
        "yosh nechada",
        "yoshing nechada",
        "yoshingiz nechada",
        "yosh nechchida",
        "yoshing nechchida",
        "yoshingiz nechchida",
        "yoshingiz nechida",
        "yoshingiz necha",
        "yoshing nechida",
        "yoshing necha",
        "yoshdasiz",
        "yoshdasan",
        "nechanchi yil",
        "nechanchi yilsiz",
        "nechanchi yilsan",
        "nechanchi yilda",
        "nechinchi yil",
        "qaysi yilsiz",
        "qaysi yilsan",
        "qaysi yil tug'ilgan",
        "tug'ilgan yilingiz",
        "tug'ilgan yil",
        "tugilgan yilingiz",
        "tugilgan yil",
        "qachon tug'ilgansiz",
        "qachon tugilgan",
        # Personal life / Family / Location
        "qayerdansiz",
        "qattansiz",
        "qayerliksiz",
        "qayerdansan",
        "qayerda yashaysiz",
        "qayerda turasiz",
        "uylanganmisiz",
        "uylangan",
        "oilalimisiz",
        "oilangiz",
        "turmush qurganmisiz",
        "erga tekkanmisiz",
        "farzandlaringiz",
        "farzand",
        "bolalaringiz",
        "shaxsiy hayot",
        "shaxsiy ma'lumot",
        "shaxsiy malumot",
        "shaxsiy savol",
        # Complaints / Meta inquiries about personal question
        "nimaga yoshing",
        "nega yoshing",
        "yoshimni so'rasam",
        "yosh haqida",
        "shaxsiy savol berdim",
        "shaxsiy savolimga",
        # Russian
        "кто вы",
        "кто ты",
        "кто это",
        "как вас зовут",
        "как тебя зовут",
        "ваше имя",
        "твое имя",
        "расскажи о себе",
        "расскажите о себе",
        "биография",
        "сколько вам лет",
        "сколько тебе лет",
        "сколько лет",
        "какой возраст",
        "ваш возраст",
        "твой возраст",
        "какого года",
        "какой год рождения",
        "когда родился",
        "когда родились",
        "дата рождения",
        "год рождения",
        "откуда вы",
        "откуда ты",
        "где живешь",
        "где вы живете",
        "где живете",
        "женат",
        "замужем",
        "семейное положение",
        "семейный статус",
        "семья",
        "дети",
        "личная жизнь",
        "личные данные",
        "личный вопрос",
        # English
        "how old are you",
        "how old are u",
        "how old r u",
        "how old",
        "what is your age",
        "what's your age",
        "your age",
        "when were you born",
        "birth date",
        "birth year",
        "who are you",
        "who are u",
        "who r u",
        "who is this",
        "what is your name",
        "what's your name",
        "tell me about yourself",
        "about yourself",
        "where are you from",
        "where do you live",
        "are you married",
        "do you have a family",
        "do you have children",
    ]

    if any(p in q for p in direct_patterns):
        return True

    # 1. Any mention of "yosh" (age) in short queries (e.g. "yoshingiz?", "yoshiz nechchi?", "yoshiz?")
    if any(w in words for w in ["yoshsiz", "yoshdasiz", "yoshdasan", "yoshingiz", "yoshing", "yoshiz"]) and len(words) <= 6:
        return True

    # 2. Short questions with "yil" (birth year), e.g. "nechi yilsiz", "yilingiz?"
    if any(w in words for w in ["yilsiz", "yilsan"]) and len(words) <= 6:
        return True

    # 3. Short question about who the bot/person is
    if len(words) <= 4:
        if any(w in words for w in ["kimsiz", "kimsan"]) or ("kim" in words and any(w in words for w in ["bu", "siz", "san", "u"])):
            return True
        if "кто" in words and any(w in words for w in ["вы", "ты", "это"]):
            return True
        if "who" in words and any(w in words for w in ["you", "u", "this"]):
            return True

    return False


def is_general_services_inquiry(text: str) -> bool:
    """Check if the user is asking about general services catalog, pricing, or wants consultation."""
    if is_personal_identity_inquiry(text):
        return False

    q = text.lower().strip()
    clean_no_punct = re.sub(r"[^\w\s]", " ", q)
    words = clean_no_punct.split()

    if not words:
        return False

    # Check if the user is complaining / asking meta-questions about why prices or services were sent
    complaint_triggers = [
        "nimaga",
        "nega",
        "sabab",
        "so'ramadim",
        "soramadim",
        "kerakmas",
        "tashlayapsan",
        "tashlayapsiz",
        "yuboryapsan",
        "yuboryapsiz",
        "почему",
        "зачем",
        "не просил",
        "не спрашивал",
        "why",
        "didn't ask",
    ]
    if any(c in q for c in complaint_triggers) and any(
        term in q for term in ["narx", "xizmat", "tarif", "price", "цен"]
    ):
        return False

    # 1. Any combination of service-related root + price/cost-related root
    # Handles typos like: xizmatoz, xizmatiz, xizmat, xizmatlar, qanfha, qancha, nechpul, narx, etc.
    price_pattern = r"\b(?:narx|qanch|qanfh|qanca|nechpul|summa|baho|qiymat|почем|скольк|цен|стоим|прайс|тариф|pricing|price|tariff|cost)\w*"
    service_pattern = r"\b(?:xizm|xzm|konsult|maslahat|advokat|yurist|uslug|услуг|консульт|consult)\w*"

    has_price_word = any(bool(re.search(price_pattern, w)) for w in words)
    has_service_word = any(bool(re.search(service_pattern, w)) for w in words)

    has_price_phrase = any(
        phrase in q
        for phrase in [
            "necha pul",
            "nech pul",
            "qancha turadi",
            "qancha boladi",
            "qancha bo'ladi",
            "qancha ekan",
            "narxi qanaqa",
            "narxi qanday",
            "narxlar qanaqa",
            "narxlar qanday",
            "сколько стоит",
            "какая цена",
            "какие расценки",
            "сколько возьмете",
            "how much",
        ]
    )

    if (has_price_word or has_price_phrase) and has_service_word:
        return True

    # 2. Standalone pricing inquiry or short question about cost
    standalone_price_phrases = [
        "narxi qancha",
        "narxi qanfha",
        "narxlar qanaqa",
        "narxlar qanday",
        "narxlari qanday",
        "narxlar",
        "narxlari",
        "narxi",
        "qancha turadi",
        "qancha boladi",
        "qancha bo'ladi",
        "qancha ekan",
        "necha pul",
        "nechpul",
        "preyskurant",
        "prikurant",
        "tariflar",
        "tarifi",
        "xizmat narxi",
        "xizmat narxlari",
        "xizmat qancha",
        "xizmatingiz qancha",
        "xizmatoz qancha",
        "xizmatoz qanfha",
        "xizmatiz qancha",
        "xizmatlar qancha",
        "xizmat haqi",
        "сколько стоит",
        "какая цена",
        "цена",
        "цены",
        "стоимость",
        "прайс",
        "тарифы",
        "почем",
        "how much does it cost",
        "what is the price",
    ]
    if any(p in q for p in standalone_price_phrases):
        return True

    # If the message is short (<= 4 words) and contains a price root (e.g. "qancha?", "qanfha?", "narxi?"):
    # Ensure it's not a unit/noun question like "necha yosh", "necha kun", "nechta bola"
    non_price_units = {
        "yosh",
        "yoshsiz",
        "yoshda",
        "yoshingiz",
        "yoshing",
        "yoshiz",
        "yil",
        "yilsiz",
        "yildasiz",
        "yilingiz",
        "kun",
        "oy",
        "soat",
        "bola",
        "kishi",
        "odam",
        "hujjat",
        "modda",
        "qonun",
    }
    if (
        len(words) <= 4
        and (has_price_word or has_price_phrase)
        and not any(w in non_price_units for w in words)
    ):
        return True

    # 3. Explicit service catalog / consultation requests
    explicit_catalog_phrases = [
        "xizmatlar",
        "xizmatlaringiz",
        "xizmatlariz",
        "xizmatoz",
        "xizmatiz",
        "qanday xizmat",
        "qanaqa xizmat",
        "nima xizmat",
        "xizmatlar ro'yxati",
        "xizmatlar royxati",
        "mavjud xizmatlar",
        "barcha xizmatlar",
        "xizmatlar haqida",
        "xizmatlaringiz haqida",
        "konsultatsiya olmoqchiman",
        "konsultatsiya olaman",
        "konsultatsiya olsak",
        "konsultatsiya narxi",
        "konsultatsiya qancha",
        "maslahat olmoqchiman",
        "maslahat olaman",
        "xizmatdan foydalan",
        "xizmatlardan foydalan",
        "xizmatlaringizdan foydalan",
        "xizmat olmoq",
        "xizmat olaman",
        "xizmat olmoqchiman",
        "какие услуги",
        "какие есть услуги",
        "список услуг",
        "перечень услуг",
        "стоимость услуг",
        "хочу воспользоваться услугой",
        "хочу воспользоваться услугами",
        "хочу заказать услугу",
        "ваши услуги",
        "хочу консультацию",
        "получить консультацию",
        "стоимость консультации",
    ]
    if any(p in q for p in explicit_catalog_phrases):
        return True

    # 4. Short intent queries (e.g. "konsultatsiya", "maslahat kerak", "yurist kerak")
    if len(words) <= 5:
        short_intent_phrases = [
            "konsultatsiya",
            "konsultatsiya kerak",
            "maslahat kerak",
            "xizmat kerak",
            "yordam kerak",
            "yurist kerak",
            "advokat kerak",
            "yuridik yordam",
            "консультация",
            "консультацию",
            "нужна консультация",
            "юридическая помощь",
            "нужен юрист",
            "нужен адвокат",
        ]
        if any(p in q for p in short_intent_phrases):
            return True

    return False


def format_services_catalog_text(services: Sequence[Service], lang: str = "uz") -> str:
    """Format rich catalog of active legal services for business chat."""
    if lang == "ru":
        lines = [
            "💼 <b>Наши квалифицированные юридические услуги и тарифы:</b>\n"
        ]
        for idx, s in enumerate(services, start=1):
            price_fmt = PaymentService.format_service_price(s.price)
            title = s.title_ru or s.title_uz
            desc = (s.description_ru or s.description_uz or "").strip()
            lines.append(f"<b>{idx}. {title}</b>\n💵 Стоимость: <b>{price_fmt}</b>")
            if desc:
                lines.append(f"ℹ️ <i>{desc}</i>")
            lines.append("")
        lines.append(
            "👉 <i>Чтобы выбрать услугу, отправьте её номер (например: <b>1</b> или <b>2</b>) или напишите название услуги.</i>"
        )
        return "\n".join(lines)

    lines = [
        "💼 <b>Bizning professional yuridik xizmatlarimiz va narxlar:</b>\n"
    ]
    for idx, s in enumerate(services, start=1):
        price_fmt = PaymentService.format_service_price(s.price)
        title = s.title_uz
        desc = (s.description_uz or "").strip()
        lines.append(f"<b>{idx}. {title}</b>\n💵 Narxi: <b>{price_fmt}</b>")
        if desc:
            lines.append(f"ℹ️ <i>{desc}</i>")
        lines.append("")
    lines.append(
        "👉 <i>Kerakli xizmatni tanlash uchun uning raqamini (masalan: <b>1</b> yoki <b>2</b>) yoki xizmat nomini yozib yuboring.</i>"
    )
    return "\n".join(lines)


def detect_service_selection(
    text: str,
    services: Sequence[Service],
    is_awaiting: bool = False,
) -> Service | None:
    """Detect which service the client selected by number, ordinal, or keywords."""
    clean = text.strip().lower()

    # 1. Number selection (e.g. "1", "2", "3-xizmat", etc.)
    if is_awaiting or clean.isdigit() or re.match(r"^[1-9]\b", clean):
        num_match = re.search(r"\b([1-9])\b", clean)
        if num_match:
            idx = int(num_match.group(1)) - 1
            if 0 <= idx < len(services):
                return services[idx]

    # If NOT awaiting choice after catalog presentation, DO NOT auto-select by keywords!
    # The client must first see all services before choosing.
    if not is_awaiting:
        return None

    # 2. Ordinals (when awaiting choice)
    ordinals = {
        "bir": 0, "birinchi": 0, "birinchisi": 0, "1-si": 0, "1-xizmat": 0,
        "ikki": 1, "ikkinchi": 1, "ikkinchisi": 1, "2-si": 1, "2-xizmat": 1,
        "uch": 2, "uchinchi": 2, "uchinchisi": 2, "3-si": 2, "3-xizmat": 2,
        "to'rt": 3, "tort": 3, "to'rtinchi": 3, "tortinchisi": 3, "4-si": 3, "4-xizmat": 3,
        "besh": 4, "beshinchi": 4, "beshinchisi": 4, "5-si": 4, "5-xizmat": 4,
        "olti": 5, "oltinchi": 5, "oltinchisi": 5, "6-si": 5, "6-xizmat": 5,
        "yetti": 6, "yettinchi": 6, "yettinchisi": 6, "7-si": 6, "7-xizmat": 6,
    }
    for word, idx in ordinals.items():
        if word in clean and 0 <= idx < len(services):
            return services[idx]

    # 3. Specific service distinctions when awaiting choice
    if "telegram" in clean or "onlayn" in clean or "online" in clean:
        for s in services:
            if "telegram" in s.title_uz.lower():
                return s

    if "office" in clean or "ofis" in clean:
        for s in services:
            if "office" in s.title_uz.lower() or "ofis" in s.title_uz.lower():
                return s

    if any(k in clean for k in ["da'vo", "davo", "ariza", "talabnoma", "pretenziya", "isk"]):
        for s in services:
            if "da'vo" in s.title_uz.lower() or s.service_type == "claim":
                return s

    if any(k in clean for k in ["shartnoma", "audit", "ekspertiza", "dogovor"]):
        for s in services:
            if "shartnoma" in s.title_uz.lower() or s.service_type == "audit":
                return s

    if any(k in clean for k in ["sudda", "sudya", "vakillik", "himoyasi"]):
        for s in services:
            if "sud" in s.title_uz.lower() or s.service_type == "court":
                return s

    if any(k in clean for k in ["biznes", "autsorsing", "kompaniya", "mchj", "oylik"]):
        for s in services:
            if "biznes" in s.title_uz.lower() or s.service_type in ("retainer", "business"):
                return s

    return None


def is_service_payment_intent(text: str) -> bool:
    """Detect if client is asking about service price, buying, or paying."""
    q = text.lower()
    keywords = [
        "narxi qancha",
        "narxi nechi",
        "qancha turadi",
        "narxlari",
        "sotib olmoq",
        "xizmatidan foydalan",
        "tolov qilmoq",
        "to'lov qilmoq",
        "to'lamoqchiman",
        "tolamoqchiman",
        "karta raqam",
        "kartangiz",
        "kartani yubor",
        "qayerga to'la",
        "qayerga tola",
        "qayerga to'lov",
        "buyurtma qilmoq",
        "hisob raqam",
        "chekni qayerga",
        "rekwizit",
        "rekvizit",
        "chek",
        "to'lov qildim",
        "tolov qildim",
        "to'ladim",
        "toladim",
    ]
    return any(k in q for k in keywords)


async def find_relevant_service(session: AsyncSession, text: str) -> Service | None:
    """Find the most relevant legal service based on client text keywords."""
    services = await PaymentService.get_active_services(session)
    if not services:
        await PaymentService.seed_default_services(session)
        services = await PaymentService.get_active_services(session)

    matched = detect_service_selection(text, services, is_awaiting=True)
    if matched:
        return matched

    return None


@router.business_connection()
async def handle_business_connection(connection: BusinessConnection) -> None:
    """Track lawyer business connection status changes."""
    status = "connected" if connection.is_enabled else "disconnected"
    logger.info(
        "Telegram Business connection update: id=%s, user=%d, status=%s",
        connection.id,
        connection.user.id,
        status,
    )


@router.business_message()
async def handle_business_message(
    message: Message,
    session: AsyncSession,
    bot: Bot,
    redis_client: Redis | None = None,
) -> None:
    """Handle messages in Telegram Business chats with payment, cheque, and manual takeover support."""
    if not message.from_user or not message.business_connection_id:
        return

    chat_id = message.chat.id
    sender_id = message.from_user.id

    # 1. Get or create the client (the person the lawyer is chatting with)
    client_tg_id = chat_id
    client_name = message.chat.full_name or "Mijoz"
    client_user, _ = await UserService.get_or_create_user(session, client_tg_id, full_name=client_name)

    # Store latest active business_connection_id for return notifications
    client_user.business_connection_id = message.business_connection_id
    await session.commit()

    # In Telegram Business (1-on-1 private chat):
    # - If sender_id == chat_id: incoming message from the client to the business account
    # - If sender_id != chat_id: outgoing manual message from the business account owner (lawyer)
    is_lawyer = (sender_id != chat_id)

    # =========================================================================
    # A. HANDLE CLIENT PHOTO (PAYMENT CHEQUE / RECEIPT)
    # =========================================================================
    if not is_lawyer and message.photo:
        photo_file_id = message.photo[-1].file_id

        # 1. Fetch latest pending or recent transaction
        stmt_tx = (
            select(Transaction)
            .where(Transaction.user_id == client_user.id)
            .order_by(Transaction.id.desc())
            .limit(1)
        )
        res_tx = await session.execute(stmt_tx)
        latest_tx = res_tx.scalar_one_or_none()

        # 2. Fetch latest user inquiry / chat context for problem snippet
        stmt_inq = (
            select(Inquiry)
            .where(Inquiry.user_id == client_user.id)
            .order_by(Inquiry.id.desc())
            .limit(1)
        )
        res_inq = await session.execute(stmt_inq)
        latest_inq = res_inq.scalar_one_or_none()

        problem_snippet = ""
        if latest_inq and latest_inq.question_text:
            problem_snippet = latest_inq.question_text
        elif latest_tx and latest_tx.transaction_ref:
            problem_snippet = f"Xizmat buyurtmasi: {latest_tx.transaction_ref}"
        else:
            recent_msgs = await ChatService.get_conversation(session, client_user.id, limit=5)
            user_texts = [m.text for m in recent_msgs if m.sender_type == "user" and m.text]
            if user_texts:
                problem_snippet = " | ".join(user_texts[-3:])

        service_title = "Yuridik xizmat / Konsultatsiya"
        if latest_tx and latest_tx.transaction_ref:
            service_title = latest_tx.transaction_ref
        elif latest_tx:
            service_title = f"Xizmat to'lovi (#{latest_tx.id})"

        # 3. Dispatch to group forum topics (Payment & Contact topics)
        await GroupNotificationService.notify_payment_receipt(
            bot=bot,
            session=session,
            user=client_user,
            photo_file_id=photo_file_id,
            service_title=service_title,
            problem_summary=problem_snippet,
            tx_id=latest_tx.id if latest_tx else None,
        )

        await GroupNotificationService.notify_contact_request(
            bot=bot,
            session=session,
            user=client_user,
            service_title=service_title,
            problem_summary=problem_snippet,
        )

        # 4. Reply to client in business chat
        ack_text = (
            "✅ <b>To'lov chekingiz qabul qilindi!</b>\n\n"
            "Tez orada mas'ul huquqshunosimiz uni tekshirib, siz bilan bog'lanadi va ishingizni ko'rib chiqishni boshlaydi."
        )
        await message.answer(text=ack_text)

        await ChatService.log_message(
            session=session,
            user_id=client_user.id,
            telegram_id=sender_id,
            sender_type="user",
            text="[To'lov cheki skrinshoti yuklandi]",
            is_business=True,
            message_type="photo",
            telegram_message_id=message.message_id,
        )
        return

    # =========================================================================
    # B. EXTRACT TEXT / VOICE
    # =========================================================================
    question_text = ""
    is_voice = False

    if message.text:
        question_text = message.text
    elif message.voice:
        is_voice = True
        if not is_lawyer:
            from pathlib import Path
            from tempfile import NamedTemporaryFile

            from app.services.ai.speech import SpeechService

            speech_service = SpeechService()
            with NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            try:
                await bot.send_chat_action(
                    chat_id=chat_id,
                    action="record_voice",
                    business_connection_id=message.business_connection_id,
                )
                file_info = await bot.get_file(message.voice.file_id)
                if file_info.file_path:
                    await bot.download_file(file_info.file_path, destination=temp_path)
                question_text = await speech_service.transcribe_audio(temp_path, language="uz")
            except Exception as e:  # noqa: BLE001
                logger.error("Failed to transcribe business voice message: %s", e)
            finally:
                if temp_path.exists():
                    temp_path.unlink()
        else:
            question_text = "[Huquqshunosning ovozli xabari]"

    # If neither text nor voice, just ignore
    if not question_text and not message.voice:
        return

    # 3. Log the incoming message
    await ChatService.log_message(
        session=session,
        user_id=client_user.id,
        telegram_id=sender_id,
        sender_type="lawyer" if is_lawyer else "user",
        text=question_text,
        is_business=True,
        message_type="voice" if is_voice else "text",
        telegram_message_id=message.message_id,
    )

    # 4. Instant Manual Takeover Mechanism & Unpause commands:
    clean_cmd = question_text.strip().lower()
    if is_lawyer and clean_cmd in ("/unpause", "/ai_on", "/ai", "ai yoq", "ai"):
        if redis_client:
            await BusinessPauseManager.resume(chat_id, redis_client)
        await message.answer(text="✅ Sun'iy intellekt yordamchisi ushbu chatda qayta faollashtirildi!")
        return

    if is_lawyer:
        if redis_client:
            await BusinessPauseManager.set_paused(
                chat_id=chat_id,
                redis_client=redis_client,
                duration_seconds=settings.BUSINESS_TAKEOVER_PAUSE_SECONDS,
            )
            logger.info(
                "Lawyer manually replied in chat %d; paused AI for %d seconds",
                chat_id,
                settings.BUSINESS_TAKEOVER_PAUSE_SECONDS,
            )
        return

    # 5. Client message: Check if chat is currently paused by lawyer takeover
    if redis_client and await BusinessPauseManager.is_paused(chat_id, redis_client):
        logger.info("AI response skipped for chat %d (Lawyer takeover active)", chat_id)
        return

    # =========================================================================
    # C. SERVICES CATALOG, SELECTION & PAYMENT ROUTING IN BUSINESS CHAT
    # =========================================================================
    found_phone = extract_phone(question_text)
    if found_phone and found_phone != client_user.phone_number:
        client_user.phone_number = found_phone
        await session.commit()
        await GroupNotificationService.notify_new_lead(
            bot=bot,
            session=session,
            user=client_user,
            purpose=question_text,
        )
        logger.info("Captured phone %s for user %d in business chat", found_phone, client_user.id)

    # 1. Read Redis state for business chat session
    awaiting_choice = False
    stored_service_id: int | None = None
    if redis_client:
        try:
            raw_awaiting = await redis_client.get(f"biz_awaiting_service:{client_user.id}")
            awaiting_choice = bool(raw_awaiting)
            raw_sid = await redis_client.get(f"biz_selected_service:{client_user.id}")
            if raw_sid:
                sid_str = raw_sid.decode() if isinstance(raw_sid, bytes) else str(raw_sid)
                if sid_str.isdigit():
                    stored_service_id = int(sid_str)
        except Exception as e:  # noqa: BLE001
            logger.warning("Redis read error in business chat: %s", e)

    # Fetch active services from DB
    services = await PaymentService.get_active_services(session)
    if not services:
        await PaymentService.seed_default_services(session)
        services = await PaymentService.get_active_services(session)

    # 2. Check if user just submitted their phone number after service prompt
    is_phone_only = (found_phone is not None and len(question_text.strip()) <= 25)
    if is_phone_only:
        target_service = None
        if stored_service_id:
            target_service = next((s for s in services if s.id == stored_service_id), None)
        if not target_service:
            target_service = services[0] if services else None

        if target_service:
            if redis_client:
                try:
                    await redis_client.delete(f"biz_awaiting_service:{client_user.id}")
                except Exception as e:  # noqa: BLE001
                    logger.debug("Failed deleting biz_awaiting_service: %s", e)

            org_settings = await OrgSettingsService.get_settings(session)
            _ = await PaymentService.create_transaction(
                session=session,
                user=client_user,
                amount=target_service.price,
                payment_method="p2p_card",
                transaction_ref=target_service.title_uz,
            )
            price_fmt = PaymentService.format_service_price(target_service.price)
            p2p_msg = (
                "💳 <b>To'lov ma'lumotlari</b>\n\n"
                f"💼 Xizmat: <b>{target_service.title_uz}</b>\n"
                f"💵 To'lov summasi: <b>{price_fmt}</b>\n\n"
                f"💳 Karta raqami: <code>{org_settings.card_number}</code>\n"
                f"👤 Qabul qiluvchi: <b>{org_settings.card_holder}</b>\n\n"
                "<i>To'lovni amalga oshirgach, to'lov cheki (skrinshot)ni ushbu chatga yuboring. "
                "Huquqshunos to'lovni tasdiqlashi bilan xizmat ko’rsatish darhol boshlanadi.</i>"
            )
            await message.answer(text=p2p_msg)
            await ChatService.log_message(
                session=session,
                user_id=client_user.id,
                telegram_id=bot.id,
                sender_type="bot",
                text=p2p_msg,
                is_business=True,
            )
            return

    # 2.5. Check if user is asking about office address / location
    if OrgSettingsService.is_office_address_inquiry(question_text):
        has_paid = await PaymentService.has_confirmed_office_consultation(session, client_user.id)
        if has_paid:
            org_settings = await OrgSettingsService.get_settings(session)
            addr_text = OrgSettingsService.format_office_address_text(org_settings, client_user.language)
            await message.answer(text=addr_text)
            await OrgSettingsService.send_office_location(
                bot=bot,
                chat_id=client_user.telegram_id,
                settings_record=org_settings,
                business_connection_id=message.business_connection_id,
            )
        else:
            addr_text = OrgSettingsService.format_office_service_notice(client_user.language)
            await message.answer(text=addr_text)
        await ChatService.log_message(
            session=session,
            user_id=client_user.id,
            telegram_id=bot.id,
            sender_type="bot",
            text=addr_text,
            is_business=True,
        )
        return

    # 2.6. Check if user is specifying their office visit time slot
    slot_type = OrgSettingsService.detect_office_time_slot(question_text)
    if slot_type:
        has_paid_office = await PaymentService.has_confirmed_office_consultation(session, client_user.id)
        if has_paid_office:
            stmt_tx = (
                select(Transaction)
                .where(Transaction.user_id == client_user.id)
                .where(Transaction.payment_status.in_(["completed", "fulfilled"]))
                .order_by(Transaction.id.desc())
                .limit(1)
            )
            res_tx = await session.execute(stmt_tx)
            recent_tx = res_tx.scalar_one_or_none()
            recent_tx_id = recent_tx.id if recent_tx else None

            slot_text, resp_text = await OrgSettingsService.register_office_slot(
                session=session,
                user_id=client_user.id,
                slot_type=slot_type,
                tx_id=recent_tx_id,
            )
            await message.answer(text=resp_text)
            await ChatService.log_message(
                session=session,
                user_id=client_user.id,
                telegram_id=bot.id,
                sender_type="bot",
                text=resp_text,
                is_business=True,
            )
            await OrgSettingsService.notify_office_slot_chosen(
                bot=bot,
                session=session,
                user_id=client_user.id,
                slot_text=slot_text,
                tx_id=recent_tx_id,
            )
            return

    # 2.7. Check if user is asking personal questions about the lawyer's identity/personal life
    if is_personal_identity_inquiry(question_text):
        low = question_text.lower()
        if any(en_w in low for en_w in ["how old", "who are you", "who are u", "what is your", "your age", "about you"]):
            personal_reply = "Unfortunately, I cannot answer personal questions. If you have any legal questions or issues, please describe them in detail."
        elif client_user.language == "ru" or any(ru_w in low for ru_w in ["кто вы", "сколько вам лет", "сколько тебе лет", "о себе"]):
            personal_reply = "К сожалению, я не могу отвечать на личные вопросы. Если у вас есть правовые вопросы, подробно опишите вашу ситуацию."
        else:
            personal_reply = "Afsusku shaxsiy savollaringizga javob bera olmayman. Agar huquqiuy masalada savollaringiz bo'lsa batafsil yozib qoldiring"
        await message.answer(text=personal_reply)
        await ChatService.log_message(
            session=session,
            user_id=client_user.id,
            telegram_id=bot.id,
            sender_type="bot",
            text=personal_reply,
            is_business=True,
        )
        return

    # 3. Check if user is inquiring generally about services catalog or pricing
    if is_general_services_inquiry(question_text):
        catalog_text = format_services_catalog_text(services, client_user.language)
        if redis_client:
            try:
                await redis_client.set(f"biz_awaiting_service:{client_user.id}", "1", ex=3600)
            except Exception as e:  # noqa: BLE001
                logger.debug("Failed setting biz_awaiting_service: %s", e)

        await message.answer(text=catalog_text)
        await ChatService.log_message(
            session=session,
            user_id=client_user.id,
            telegram_id=bot.id,
            sender_type="bot",
            text=catalog_text,
            is_business=True,
        )
        return

    # 4. Check if user selected a service (by number, ordinal, or keyword)
    chosen_service = detect_service_selection(question_text, services, is_awaiting=awaiting_choice)
    if chosen_service:
        if redis_client:
            try:
                await redis_client.set(f"biz_selected_service:{client_user.id}", str(chosen_service.id), ex=7200)
                await redis_client.delete(f"biz_awaiting_service:{client_user.id}")
            except Exception as e:  # noqa: BLE001
                logger.debug("Failed setting biz_selected_service: %s", e)
        price_fmt = PaymentService.format_service_price(chosen_service.price)

        # If user has no phone number, ask for phone first
        if not client_user.phone_number:
            prompt_phone_text = (
                f"💼 <b>Siz tanlagan xizmat: {chosen_service.title_uz}</b>\n"
                f"💵 Rasmiy xizmat narxi: <b>{price_fmt}</b>\n\n"
                "Xizmatni rasmiylashtirish va to'lov rekvizitlarini yuborishimiz uchun, "
                "iltimos, <b>telefon raqamingizni</b> yozib qoldiring (masalan: <code>+998901234567</code>):"
            )
            await message.answer(text=prompt_phone_text)
            await ChatService.log_message(
                session=session,
                user_id=client_user.id,
                telegram_id=bot.id,
                sender_type="bot",
                text=prompt_phone_text,
                is_business=True,
            )
            return

        # User already has phone number: issue payment details immediately
        org_settings = await OrgSettingsService.get_settings(session)
        _ = await PaymentService.create_transaction(
            session=session,
            user=client_user,
            amount=chosen_service.price,
            payment_method="p2p_card",
            transaction_ref=chosen_service.title_uz,
        )
        p2p_msg = (
            "💳 <b>To'lov ma'lumotlari</b>\n\n"
            f"💼 Xizmat: <b>{chosen_service.title_uz}</b>\n"
            f"💵 To'lov summasi: <b>{price_fmt}</b>\n\n"
            f"💳 Karta raqami: <code>{org_settings.card_number}</code>\n"
            f"👤 Qabul qiluvchi: <b>{org_settings.card_holder}</b>\n\n"
            "<i>To'lovni amalga oshirgach, to'lov cheki (skrinshot)ni ushbu chatga yuboring. "
            "Huquqshunos to'lovni tasdiqlashi bilan xizmat ko’rsatish darhol boshlanadi.</i>"
        )
        await message.answer(text=p2p_msg)
        await ChatService.log_message(
            session=session,
            user_id=client_user.id,
            telegram_id=bot.id,
            sender_type="bot",
            text=p2p_msg,
            is_business=True,
        )
        return

    # 5. Check if client explicitly asks for payment card / how to pay
    if is_service_payment_intent(question_text):
        target_service = None
        if stored_service_id:
            target_service = next((s for s in services if s.id == stored_service_id), None)
        if not target_service:
            # If user hasn't selected a service yet, present the full services catalog first
            catalog_text = format_services_catalog_text(services, client_user.language)
            if redis_client:
                try:
                    await redis_client.set(f"biz_awaiting_service:{client_user.id}", "1", ex=3600)
                except Exception as e:  # noqa: BLE001
                    logger.debug("Failed setting biz_awaiting_service: %s", e)

            await message.answer(text=catalog_text)
            await ChatService.log_message(
                session=session,
                user_id=client_user.id,
                telegram_id=bot.id,
                sender_type="bot",
                text=catalog_text,
                is_business=True,
            )
            return

        price_fmt = PaymentService.format_service_price(target_service.price)
        if not client_user.phone_number:
            prompt_phone_text = (
                f"💼 <b>{target_service.title_uz}</b>\n"
                f"💵 Rasmiy xizmat narxi: <b>{price_fmt}</b>\n\n"
                "Xizmatni rasmiylashtirish va to'lov rekvizitlarini yuborishimiz uchun, "
                "iltimos, <b>telefon raqamingizni</b> yozib qoldiring (masalan: <code>+998901234567</code>):"
            )
            await message.answer(text=prompt_phone_text)
            await ChatService.log_message(
                session=session,
                user_id=client_user.id,
                telegram_id=bot.id,
                sender_type="bot",
                text=prompt_phone_text,
                is_business=True,
            )
            return

        org_settings = await OrgSettingsService.get_settings(session)
        _ = await PaymentService.create_transaction(
            session=session,
            user=client_user,
            amount=target_service.price,
            payment_method="p2p_card",
            transaction_ref=target_service.title_uz,
        )
        p2p_msg = (
            "💳 <b>To'lov ma'lumotlari</b>\n\n"
            f"💼 Xizmat: <b>{target_service.title_uz}</b>\n"
            f"💵 To'lov summasi: <b>{price_fmt}</b>\n\n"
            f"💳 Karta raqami: <code>{org_settings.card_number}</code>\n"
            f"👤 Qabul qiluvchi: <b>{org_settings.card_holder}</b>\n\n"
            "<i>To'lovni amalga oshirgach, to'lov cheki (skrinshot)ni ushbu chatga yuboring. "
            "Huquqshunos to'lovni tasdiqlashi bilan xizmat ko’rsatish darhol boshlanadi.</i>"
        )
        await message.answer(text=p2p_msg)
        await ChatService.log_message(
            session=session,
            user_id=client_user.id,
            telegram_id=bot.id,
            sender_type="bot",
            text=p2p_msg,
            is_business=True,
        )
        return

    # =========================================================================
    # D. GENERATE UNDETECTABLE HUMAN ATTORNEY LEGAL REPLY
    # =========================================================================
    if question_text:
        typing_delay = min(max(len(question_text) * 0.01, 1.5), 3.5)
        try:
            await bot.send_chat_action(
                chat_id=chat_id,
                action="typing",
                business_connection_id=message.business_connection_id,
            )
            await asyncio.sleep(typing_delay)

            history_context = await ChatService.get_recent_history_context(
                session=session,
                user_id=client_user.id,
                limit=10,
                language=client_user.language or "uz",
            )
            analysis = await llm_service.analyze_legal_inquiry(
                question=question_text,
                language=client_user.language or "uz",
                conversation_history=history_context,
            )

            await message.answer(text=analysis.response_text)
            logger.info("Sent AI business response on behalf of lawyer in chat %d", chat_id)

            await ChatService.log_message(
                session=session,
                user_id=client_user.id,
                telegram_id=bot.id,
                sender_type="bot",
                text=analysis.response_text,
                is_business=True,
            )

        except Exception as e:  # noqa: BLE001
            logger.error("Failed to generate or send business reply: %s", e)
