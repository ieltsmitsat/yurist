"""Legal inquiry handlers for text and voice messages."""

import asyncio
import logging
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from aiogram import Bot, F, Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.i18n import t
from app.bot.keyboards.keyboards import cta_keyboard, phone_request_kb
from app.core.config import settings
from app.db.models.user import User
from app.db.session import AsyncSessionLocal
from app.services.access_service import AccessService
from app.services.chat_service import ChatService
from app.services.inquiry_debouncer import BufferedMessage, inquiry_debouncer
from app.services.inquiry_service import InquiryService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router(name="inquiry_router")
inquiry_service = InquiryService()


def is_general_or_private(message: Message) -> bool:
    """Ensure bot only responds in private chats or the General topic of supergroups."""
    if not message.chat:
        return False

    if message.chat.type == "private":
        return True

    # Telegram API sets is_topic_message = True for all forum topics other than General
    if getattr(message, "is_topic_message", False):
        return False

    # message_thread_id is None for General (or 1 in some client configurations)
    thread_id = getattr(message, "message_thread_id", None)
    return thread_id is None or thread_id == 1


router.message.filter(is_general_or_private)


async def _simulate_typing(bot: Bot, chat_id: int, duration: float = 1.5) -> None:
    """Simulate realistic human typing indicator in Telegram."""
    try:
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        await asyncio.sleep(duration)
    except Exception as e:  # noqa: BLE001
        logger.debug("Typing action simulation failed: %s", e)


async def _send_safe_response(
    message: Message,
    text: str,
    reply_markup: Any = None,
) -> None:
    """Send legal response safely handling length limits and markdown/HTML formatting."""
    # Convert markdown bold **text** to <b>text</b>
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)

    max_len = 3900
    if len(cleaned) <= max_len:
        try:
            await message.answer(cleaned, reply_markup=reply_markup, parse_mode="HTML")
        except Exception:  # noqa: BLE001
            await message.answer(text, reply_markup=reply_markup, parse_mode=None)
        return

    # Split into paragraphs if longer
    chunks: list[str] = []
    current: str = ""
    for paragraph in cleaned.split("\n\n"):
        if len(current) + len(paragraph) + 2 > max_len:
            if current:
                chunks.append(current.strip())
            current = paragraph + "\n\n"
        else:
            current += paragraph + "\n\n"
    if current:
        chunks.append(current.strip())

    for idx, chunk in enumerate(chunks):
        kb = reply_markup if idx == len(chunks) - 1 else None
        try:
            await message.answer(chunk, reply_markup=kb, parse_mode="HTML")
        except Exception:  # noqa: BLE001
            await message.answer(chunk, reply_markup=kb, parse_mode=None)


async def _notify_admin_high_risk(
    bot: Bot,
    user: User,
    question: str,
    risk_score: int,
) -> None:
    """Send immediate alert to lawyer/admin group for high-risk cases."""
    if not settings.ADMIN_GROUP_ID:
        return

    alert_text = (
        "🚨 <b>DIQQAT: YUQORI XAVFLI YANGI LID (HIGH RISK)!</b>\n\n"
        f"👤 <b>Mijoz:</b> {user.full_name or 'Noma\'lum'}\n"
        f"📱 <b>Telefon:</b> {user.phone_number or 'Ko\'rsatilmagan'}\n"
        f"🔴 <b>Xavf bali:</b> {risk_score}/100\n"
        f"💬 <b>Savol:</b> {question[:300]}...\n\n"
        "👉 Huquqshunos aralashuvi va zudlik bilan qo'ng'iroq qilish tavsiya etiladi."
    )
    try:
        await bot.send_message(chat_id=settings.ADMIN_GROUP_ID, text=alert_text)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to send high-risk alert to admin group: %s", e)
        # Handle automatic migration from normal group to supergroup
        if "migrated to a supergroup with id" in str(e):
            import re

            m = re.search(r"id (-?\d+)", str(e))
            if m:
                new_chat_id = int(m.group(1))
                try:
                    await bot.send_message(chat_id=new_chat_id, text=alert_text)
                    logger.info("Successfully sent alert to migrated supergroup: %d", new_chat_id)
                except Exception as retry_err:  # noqa: BLE001
                    logger.warning("Retry to supergroup %d failed: %s", new_chat_id, retry_err)


async def _check_preconditions(
    message: Message,
    user: User | None,
    session: AsyncSession | None = None,
    phone_key: str = "phone_required",
    balance_key: str = "balance_exhausted",
) -> bool:
    """Check phone verification and question balance. Returns True if user can proceed."""
    lang = user.language if user else "uz"

    # Lawyers have unrestricted unlimited messaging access without phone or balance gates
    if user:
        if UserService.is_lawyer(user):
            return True
        if session and await AccessService.is_lawyer(session, user.telegram_id):
            await UserService.sync_lawyer_status(session, user.telegram_id, is_active_lawyer=True)
            return True

    if (not user or not user.phone_number) and message.chat.type == "private":
        warn_msg = t(phone_key, lang)
        await message.answer(warn_msg, reply_markup=phone_request_kb(lang))
        if session and user:
            await ChatService.log_message(
                session=session,
                user_id=user.id,
                telegram_id=user.telegram_id,
                sender_type="bot",
                text=warn_msg,
            )
        return False

    if user and not await UserService.has_questions_available(user, session=session):
        balance_msg = t(balance_key, lang)
        await message.answer(balance_msg, reply_markup=cta_keyboard("consultation", lang))
        if session:
            await ChatService.log_message(
                session=session,
                user_id=user.id,
                telegram_id=user.telegram_id,
                sender_type="bot",
                text=balance_msg,
            )
        return False

    return True


@router.message(F.text.in_(["💬 Yuridik savol berish", "💬 Задать правовой вопрос"]))
async def handle_inquiry_button_click(
    message: Message,
    session: AsyncSession | None = None,
    user: User | None = None,
) -> None:
    """Handle click on 'Ask Legal Question' button from main menu."""
    if not message.from_user or not user:
        return

    if not await _check_preconditions(
        message, user, session=session, phone_key="phone_required_button"
    ):
        return

    lang = user.language if user else "uz"
    await message.answer(t("inquiry_invite", lang))


async def process_aggregated_inquiry(
    user: User,
    batch: list[BufferedMessage],
    bot: Bot,
) -> None:
    """Process a batch of aggregated messages from a user as a single legal inquiry."""
    if not batch:
        return

    last_message = batch[-1].message
    batch_msg_ids = [m.logged_msg_id for m in batch]
    combined_text = "\n".join(m.text.strip() for m in batch if m.text.strip())

    if not combined_text:
        return

    async with AsyncSessionLocal() as session:
        # Reload user from DB for fresh state (balance, subscription, language)
        stmt = select(User).where(User.id == user.id)
        res = await session.execute(stmt)
        fresh_user = res.scalar_one_or_none() or user

        # 1. Check preconditions (phone verification and question balance)
        if not await _check_preconditions(last_message, fresh_user, session=session):
            return

        lang = fresh_user.language or "uz"

        # 2. Check if combined text is ONLY a greeting
        clean_text = combined_text.strip().lower()
        greetings = {
            "salom",
            "assalomu alaykum",
            "assalom",
            "assalomu aleykum",
            "salomalaykum",
            "privet",
            "привет",
            "здравствуйте",
            "добрый день",
            "salom yaxshimisiz",
            "assalomu alaykum yaxshimisiz",
            "salom salom",
        }
        if clean_text in greetings:
            greet_reply = t("greeting_reply", lang)
            await last_message.answer(greet_reply)
            await ChatService.log_message(
                session=session,
                user_id=fresh_user.id,
                telegram_id=fresh_user.telegram_id,
                sender_type="bot",
                text=greet_reply,
            )
            return

        clean_normalized = re.sub(r"[^\w\s]", "", clean_text).strip()
        words = clean_normalized.split()
        thanks_phrases = {
            "rahmat",
            "raxmat",
            "katta rahmat",
            "katta raxmat",
            "rahmat kattakon",
            "raxmat kattakon",
            "rahmat sizga",
            "raxmat sizga",
            "katta rahmat sizga",
            "sog boling",
            "sog buling",
            "salomat boling",
            "tashakkur",
            "katta tashakkur",
            "spasibo",
            "bolshoe spasibo",
            "bolshoye spasibo",
            "spasibo bolshoe",
            "spasibo bolshoye",
            "blagodaryu",
            "спасибо",
            "большое спасибо",
            "спасибо большое",
            "благодарю",
            "благодарствую",
        }
        is_thanks = clean_normalized in thanks_phrases or (
            "?" not in combined_text
            and len(words) <= 4
            and (
                any(w in {"rahmat", "raxmat", "tashakkur", "spasibo", "спасибо", "благодарю"} for w in words)
                or ("sog" in words and any(b in words for b in ("boling", "buling")))
                or ("salomat" in words and any(b in words for b in ("boling", "buling")))
            )
        )
        if is_thanks:
            thanks_reply = (
                "Salomat bo’ling! Agar yana shunga o'xshash huquqiy savollaringiz bo'lsa bemalol bizga murojaat qilishingiz mumkin. Ishlaringizga omad tilayman!"
                if lang == "uz"
                else "Пожалуйста! Если у вас возникнут похожие юридические вопросы, вы всегда можете обратиться к нам. Удачи в ваших делах!"
            )
            await last_message.answer(thanks_reply)
            await ChatService.log_message(
                session=session,
                user_id=fresh_user.id,
                telegram_id=fresh_user.telegram_id,
                sender_type="bot",
                text=thanks_reply,
            )
            return

        # Check office address / location inquiry
        from app.db.models.transaction import Transaction
        from app.services.org_settings_service import OrgSettingsService
        from app.services.payment_service import PaymentService

        if OrgSettingsService.is_office_address_inquiry(combined_text):
            has_paid = await PaymentService.has_confirmed_office_consultation(session, fresh_user.id)
            if has_paid:
                org_settings = await OrgSettingsService.get_settings(session)
                addr_text = OrgSettingsService.format_office_address_text(org_settings, lang)
                await last_message.answer(addr_text)
                await OrgSettingsService.send_office_location(
                    bot=bot,
                    chat_id=fresh_user.telegram_id,
                    settings_record=org_settings,
                )
            else:
                addr_text = OrgSettingsService.format_office_service_notice(lang)
                await last_message.answer(addr_text)
            await ChatService.log_message(
                session=session,
                user_id=fresh_user.id,
                telegram_id=fresh_user.telegram_id,
                sender_type="bot",
                text=addr_text,
            )
            return

        # Check office visit time slot selection
        slot_type = OrgSettingsService.detect_office_time_slot(combined_text)
        if slot_type:
            has_paid_office = await PaymentService.has_confirmed_office_consultation(session, fresh_user.id)
            if has_paid_office:
                stmt_tx = (
                    select(Transaction)
                    .where(Transaction.user_id == fresh_user.id)
                    .where(Transaction.payment_status.in_(["completed", "fulfilled"]))
                    .order_by(Transaction.id.desc())
                    .limit(1)
                )
                res_tx = await session.execute(stmt_tx)
                recent_tx = res_tx.scalar_one_or_none()
                recent_tx_id = recent_tx.id if recent_tx else None

                slot_text, resp_text = await OrgSettingsService.register_office_slot(
                    session=session,
                    user_id=fresh_user.id,
                    slot_type=slot_type,
                    tx_id=recent_tx_id,
                )
                await last_message.answer(resp_text)
                await ChatService.log_message(
                    session=session,
                    user_id=fresh_user.id,
                    telegram_id=fresh_user.telegram_id,
                    sender_type="bot",
                    text=resp_text,
                )
                await OrgSettingsService.notify_office_slot_chosen(
                    bot=bot,
                    session=session,
                    user_id=fresh_user.id,
                    slot_text=slot_text,
                    tx_id=recent_tx_id,
                )
                return

        # Check personal identity inquiry
        from app.bot.handlers.business.messages import (
            is_general_services_inquiry,
            is_personal_identity_inquiry,
        )

        if is_personal_identity_inquiry(combined_text):
            low = combined_text.lower()
            if any(en_w in low for en_w in ["how old", "who are you", "who are u", "what is your", "your age", "about you"]):
                personal_reply = "Unfortunately, I cannot answer personal questions. If you have any legal questions or issues, please describe them in detail."
            elif lang == "ru" or any(ru_w in low for ru_w in ["кто вы", "сколько вам лет", "сколько тебе лет", "о себе"]):
                personal_reply = "К сожалению, я не могу отвечать на личные вопросы. Если у вас есть правовые вопросы, подробно опишите вашу ситуацию."
            else:
                personal_reply = "Afsusku shaxsiy savollaringizga javob bera olmayman. Agar huquqiuy masalada savollaringiz bo'lsa batafsil yozib qoldiring"
            await last_message.answer(personal_reply)
            await ChatService.log_message(
                session=session,
                user_id=fresh_user.id,
                telegram_id=fresh_user.telegram_id,
                sender_type="bot",
                text=personal_reply,
            )
            return

        # Check general services catalog or consultation request
        if is_general_services_inquiry(combined_text):
            from app.bot.handlers.public.services import handle_services_menu

            await handle_services_menu(last_message, session, fresh_user)
            return

        if len(clean_text) < 6:
            too_short_msg = t("too_short", lang)
            await last_message.answer(too_short_msg)
            await ChatService.log_message(
                session=session,
                user_id=fresh_user.id,
                telegram_id=fresh_user.telegram_id,
                sender_type="bot",
                text=too_short_msg,
            )
            return

        # 3. Simulate human typing
        typing_delay = min(max(len(combined_text) * 0.005, 1.0), 2.5)
        await _simulate_typing(bot, fresh_user.telegram_id, duration=typing_delay)

        # 4. Process inquiry with AI Persona, RAG, and conversation history
        try:
            _inquiry, analysis = await inquiry_service.process_text_inquiry(
                session=session,
                user=fresh_user,
                question_text=combined_text,
                exclude_message_ids=batch_msg_ids,
            )

            # 5. Send legal response safely
            reply_kb = (
                cta_keyboard(analysis.cta_type, lang)
                if analysis.is_legal_case and analysis.cta_type != "none"
                else None
            )
            await _send_safe_response(last_message, analysis.response_text, reply_kb)
            await ChatService.log_message(
                session=session,
                user_id=fresh_user.id,
                telegram_id=fresh_user.telegram_id,
                sender_type="bot",
                text=analysis.response_text,
            )

            # 6. Notify admin if high risk
            if analysis.is_legal_case and analysis.risk_level == "high":
                await _notify_admin_high_risk(bot, fresh_user, combined_text, analysis.risk_score)

            # 7. Notify supergroup forum topics for new lead
            from app.services.group_notification_service import GroupNotificationService

            if fresh_user.lead_status in ("verified_lead", "new"):
                await GroupNotificationService.notify_new_lead(
                    bot=bot,
                    session=session,
                    user=fresh_user,
                    purpose=combined_text,
                )
                fresh_user.lead_status = "lead_notified"
                await session.commit()

        except Exception as e:  # noqa: BLE001
            logger.error("Error handling aggregated inquiry for user #%d: %s", fresh_user.id, e)
            err_msg = t("error_text_inquiry", lang)
            await last_message.answer(err_msg)
            await ChatService.log_message(
                session=session,
                user_id=fresh_user.id,
                telegram_id=fresh_user.telegram_id,
                sender_type="bot",
                text=err_msg,
            )


# Wire the debouncer processor
inquiry_debouncer.set_processor(process_aggregated_inquiry)


@router.message(
    F.text
    & ~F.text.startswith("/")
    & ~F.text.in_(
        [
            "💬 Yuridik savol berish",
            "💬 Задать правовой вопрос",
            "📑 Hujjat auditi",
            "📑 Аудит документа",
            "💼 Xizmatlar va Narxlar",
            "💼 Услуги и Цены",
            "👥 Taklif qilish (+1 savol)",
            "👥 Пригласить (+1 вопрос)",
            "🆘 Favqulodda yordam (SOS)",
            "🆘 Экстренная помощь (SOS)",
            "⚙️ Sozlamalar",
            "⚙️ Настройки",
        ]
    )
)
async def handle_text_inquiry(
    message: Message,
    session: AsyncSession,
    bot: Bot,
    user: User | None = None,
) -> None:
    """Handle text legal inquiry with message debouncing and aggregation."""
    if not message.from_user or not message.text or not user:
        return

    # 1. Log incoming user message immediately so it's recorded in real time
    logged_msg = await ChatService.log_message(
        session=session,
        user_id=user.id,
        telegram_id=user.telegram_id,
        sender_type="user",
        text=message.text,
        telegram_message_id=message.message_id,
    )

    # 2. Add to debounce aggregator (groups multiple consecutive messages into 1 inquiry)
    await inquiry_debouncer.add_message(
        user=user,
        message=message,
        logged_msg_id=logged_msg.id,
        bot=bot,
    )


@router.message(F.voice)
async def handle_voice_inquiry(
    message: Message,
    session: AsyncSession,
    bot: Bot,
    user: User | None = None,
) -> None:
    """Handle voice memo inquiry (STT via Gemini + Legal analysis)."""
    if not message.from_user or not message.voice or not user:
        return

    if not await _check_preconditions(
        message, user,
        session=session,
        phone_key="phone_required_voice",
        balance_key="balance_exhausted_voice",
    ):
        return

    lang = user.language if user else "uz"

    # Download voice memo into temp file safely
    with NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        await bot.send_chat_action(chat_id=message.chat.id, action="record_voice")
        file_info = await bot.get_file(message.voice.file_id)
        if file_info.file_path:
            await bot.download_file(file_info.file_path, destination=temp_path)

        # Transcribe & process
        await _simulate_typing(bot, message.chat.id, duration=1.5)
        inquiry, analysis = await inquiry_service.process_voice_inquiry(
            session=session,
            user=user,
            audio_path=temp_path,
        )

        reply_kb = (
            cta_keyboard(analysis.cta_type, lang)
            if analysis.is_legal_case and analysis.cta_type != "none"
            else None
        )
        response_text = analysis.response_text
        if inquiry.stt_transcript:
            response_text = f'{t("voice_transcript_prefix", lang, transcript=inquiry.stt_transcript[:100])}\n\n{response_text}'

        await _send_safe_response(message, response_text, reply_kb)

        # Log voice message and bot reply
        await ChatService.log_message(
            session=session,
            user_id=user.id,
            telegram_id=user.telegram_id,
            sender_type="user",
            text=inquiry.stt_transcript or "[Ovozli murojaat]",
            message_type="voice",
            telegram_message_id=message.message_id,
        )
        await ChatService.log_message(
            session=session,
            user_id=user.id,
            telegram_id=user.telegram_id,
            sender_type="bot",
            text=analysis.response_text,
        )

        if analysis.is_legal_case and analysis.risk_level == "high":
            await _notify_admin_high_risk(
                bot, user, inquiry.stt_transcript or "Ovozli murojaat", analysis.risk_score
            )

        # Notify supergroup forum topics for new lead
        if user.lead_status in ("verified_lead", "new"):
            from app.services.group_notification_service import GroupNotificationService

            await GroupNotificationService.notify_new_lead(
                bot=bot,
                session=session,
                user=user,
                purpose=inquiry.stt_transcript or "Ovozli murojaat",
            )
            user.lead_status = "lead_notified"
            await session.commit()

    except Exception as e:  # noqa: BLE001
        logger.error("Error processing voice inquiry: %s", e)
        err_msg = t("error_voice_inquiry", lang)
        await message.answer(err_msg)
        await ChatService.log_message(
            session=session,
            user_id=user.id,
            telegram_id=user.telegram_id,
            sender_type="bot",
            text=err_msg,
        )
    finally:
        if temp_path.exists():
            temp_path.unlink()


@router.message(F.photo)
async def handle_photo_receipt(
    message: Message,
    session: AsyncSession,
    bot: Bot,
    user: User | None = None,
) -> None:
    """Handle photo uploads (usually payment receipts) and dispatch to payment and contact topics."""
    if not message.photo or not user:
        return

    lang = user.language if user else "uz"
    photo_file_id = message.photo[-1].file_id

    from app.db.models.inquiry import Inquiry
    from app.db.models.transaction import Transaction
    from app.services.group_notification_service import GroupNotificationService

    # 1. Fetch latest pending or completed transaction for context
    stmt_tx = (
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.id.desc())
        .limit(1)
    )
    res_tx = await session.execute(stmt_tx)
    latest_tx = res_tx.scalar_one_or_none()

    # 2. Fetch latest user inquiry for problem context
    stmt_inq = (
        select(Inquiry)
        .where(Inquiry.user_id == user.id)
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
    elif latest_tx:
        problem_snippet = f"Tranzaksiya #{latest_tx.id}"

    service_title = "Yuridik xizmat / Konsultatsiya"
    if latest_tx and latest_tx.transaction_ref:
        service_title = latest_tx.transaction_ref
    elif latest_tx:
        service_title = f"Xizmat to'lovi (#{latest_tx.id})"

    # 3. Dispatch to group forum topics
    await GroupNotificationService.notify_payment_receipt(
        bot=bot,
        session=session,
        user=user,
        photo_file_id=photo_file_id,
        service_title=service_title,
        problem_summary=problem_snippet,
        tx_id=latest_tx.id if latest_tx else None,
    )

    await GroupNotificationService.notify_contact_request(
        bot=bot,
        session=session,
        user=user,
        service_title=service_title,
        problem_summary=problem_snippet,
    )

    # 4. Acknowledge receipt to user
    await message.answer(t("photo_receipt", lang))
    await ChatService.log_message(
        session=session,
        user_id=user.id,
        telegram_id=user.telegram_id,
        sender_type="user",
        text="[To'lov cheki skrinshoti yuklandi]",
        message_type="photo",
        telegram_message_id=message.message_id,
    )
