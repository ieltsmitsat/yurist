import asyncio
import logging

from aiogram import Bot, Router
from aiogram.types import BusinessConnection, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import BusinessPauseManager
from app.services.ai.llm_client import LLMService
from app.services.chat_service import ChatService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router(name="business_router")
llm_service = LLMService()


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
    """Handle messages in Telegram Business chats with automatic 30-min pause."""
    if not message.from_user or not message.business_connection_id:
        return

    chat_id = message.chat.id
    sender_id = message.from_user.id

    # 1. Get or create the client (the person the lawyer is chatting with)
    client_tg_id = chat_id
    client_name = message.chat.full_name or "Mijoz"
    client_user, _ = await UserService.get_or_create_user(session, client_tg_id, full_name=client_name)

    # 2. Extract text or transcribe voice
    # Support multiple lawyers/admins for manual takeover
    admin_ids: set[int] = set()
    if settings.LAWYER_TELEGRAM_ID:
        admin_ids.add(settings.LAWYER_TELEGRAM_ID)
    if settings.ADMIN_TELEGRAM_IDS:
        for raw_id in settings.ADMIN_TELEGRAM_IDS.split(","):
            raw_id = raw_id.strip()
            if raw_id.isdigit():
                admin_ids.add(int(raw_id))
    is_lawyer = sender_id in admin_ids
    question_text = ""
    is_voice = False

    if message.text:
        question_text = message.text
    elif message.voice:
        is_voice = True
        if not is_lawyer: # We don't need to transcribe lawyer's voice notes sent manually
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
            question_text = "[Advokatning ovozli xabari]"

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

    # 4. Instant Manual Takeover Mechanism:
    if is_lawyer:
        if redis_client:
            await BusinessPauseManager.set_paused(
                chat_id=chat_id,
                redis_client=redis_client,
                duration_seconds=settings.BUSINESS_TAKEOVER_PAUSE_SECONDS,
            )
            logger.info("Lawyer manually replied in chat %d; paused AI for 30 minutes", chat_id)
        return

    # 5. Client message: Check if chat is currently paused by lawyer takeover
    if redis_client and await BusinessPauseManager.is_paused(chat_id, redis_client):
        logger.info("AI response skipped for chat %d (Lawyer takeover active)", chat_id)
        return

    # 6. Generate Undetectable human attorney reply
    if question_text:
        typing_delay = min(max(len(question_text) * 0.01, 1.5), 3.5)
        try:
            await bot.send_chat_action(
                chat_id=chat_id,
                action="typing",
                business_connection_id=message.business_connection_id,
            )
            await asyncio.sleep(typing_delay)

            analysis = await llm_service.analyze_legal_inquiry(
                question=question_text,
                language="uz",
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

