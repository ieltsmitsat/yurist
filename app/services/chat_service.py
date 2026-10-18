"""Chat message persistence and dialog history service."""

import logging
from collections.abc import Sequence
from typing import Any

from aiogram import Bot
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat_message import ChatMessage
from app.db.models.inquiry import Inquiry
from app.db.models.user import User

logger = logging.getLogger(__name__)


class ChatService:
    """Manages recording and querying unified chat conversations between users, bot, and lawyers."""

    @classmethod
    async def log_message(
        cls,
        session: AsyncSession,
        user_id: int,
        telegram_id: int,
        sender_type: str,  # "user", "bot", "lawyer"
        text: str | None,
        message_type: str = "text",
        telegram_message_id: int | None = None,
        is_business: bool = False,
        media_url: str | None = None,
    ) -> ChatMessage:
        """Persist a message in the chat history ledger."""
        msg = ChatMessage(
            user_id=user_id,
            telegram_id=telegram_id,
            sender_type=sender_type,
            message_type=message_type,
            text=text,
            media_url=media_url,
            telegram_message_id=telegram_message_id,
            is_business=is_business,
        )
        session.add(msg)
        await session.commit()
        await session.refresh(msg)
        logger.debug(
            "Logged chat message #%d for user #%d (%s): %s",
            msg.id,
            user_id,
            sender_type,
            (text or "")[:50],
        )
        return msg

    @classmethod
    async def log_user_message(
        cls,
        session: AsyncSession,
        user: "User",
        sender_type: str,
        text: str | None,
        message_type: str = "text",
        telegram_message_id: int | None = None,
        is_business: bool = False,
        media_url: str | None = None,
    ) -> "ChatMessage":
        """Convenience wrapper that extracts user_id and telegram_id from a User object."""
        return await cls.log_message(
            session=session,
            user_id=user.id,
            telegram_id=user.telegram_id,
            sender_type=sender_type,
            text=text,
            message_type=message_type,
            telegram_message_id=telegram_message_id,
            is_business=is_business,
            media_url=media_url,
        )

    @classmethod
    async def get_conversation(
        cls,
        session: AsyncSession,
        user_id: int,
        limit: int = 150,
    ) -> Sequence[ChatMessage]:
        """Fetch chronological message stream for a specific user."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        res = await session.execute(stmt)
        return res.scalars().all()

    @classmethod
    async def get_recent_history_context(
        cls,
        session: AsyncSession,
        user_id: int,
        limit: int = 10,
        exclude_message_ids: Sequence[int] | None = None,
        language: str = "uz",
    ) -> str | None:
        """Fetch recent conversation history formatted for LLM context memory.

        Retrieves the latest messages between the user and the bot/lawyer,
        ordered chronologically, so the AI remembers past discussions across days.
        """
        stmt = select(ChatMessage).where(ChatMessage.user_id == user_id)
        if exclude_message_ids:
            stmt = stmt.where(ChatMessage.id.not_in(exclude_message_ids))
        stmt = stmt.order_by(ChatMessage.created_at.desc()).limit(limit)

        res = await session.execute(stmt)
        messages = list(reversed(res.scalars().all()))

        user_label = "Клиент" if language == "ru" else "Mijoz"
        lawyer_label = "Адвокат" if language == "ru" else "Advokat"
        bot_label = "Юрист (Бот)" if language == "ru" else "Yurist (Bot)"

        # Fallback to Inquiries table if ChatMessage has no previous records
        if not messages:
            stmt_inq = (
                select(Inquiry)
                .where(Inquiry.user_id == user_id)
                .order_by(Inquiry.created_at.desc())
                .limit(3)
            )
            res_inq = await session.execute(stmt_inq)
            inquiries = list(reversed(res_inq.scalars().all()))
            if not inquiries:
                return None
            lines: list[str] = []
            for inq in inquiries:
                q = (inq.question_text or inq.stt_transcript or "").strip()
                ans = (inq.final_response or inq.ai_draft_response or "").strip()
                if q:
                    lines.append(f"{user_label}: {q}")
                if ans:
                    clean_ans = ans.split("```json")[0].strip()
                    lines.append(f"{lawyer_label}: {clean_ans}")
            return "\n".join(lines) if lines else None

        lines = []
        for m in messages:
            if not m.text:
                continue
            role = user_label if m.sender_type == "user" else (lawyer_label if m.sender_type == "lawyer" else bot_label)
            time_prefix = ""
            if m.created_at:
                time_prefix = f"[{m.created_at.strftime('%Y-%m-%d %H:%M')}] "
            clean_text = m.text.split("```json")[0].strip()
            if clean_text:
                lines.append(f"{time_prefix}{role}: {clean_text}")

        return "\n".join(lines) if lines else None

    @classmethod
    async def get_dialogs_list(
        cls,
        session: AsyncSession,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List all active dialog threads ordered by latest activity."""
        # 1. Fetch users ordered by their latest message or inquiry
        stmt_users = select(User).order_by(User.created_at.desc()).limit(limit)
        res_users = await session.execute(stmt_users)
        users = res_users.scalars().all()

        dialogs: list[dict[str, Any]] = []
        for u in users:
            # Get latest message
            stmt_last_msg = (
                select(ChatMessage)
                .where(ChatMessage.user_id == u.id)
                .order_by(ChatMessage.created_at.desc())
                .limit(1)
            )
            res_msg = await session.execute(stmt_last_msg)
            last_msg = res_msg.scalar_one_or_none()

            # Message count
            stmt_cnt = select(func.count(ChatMessage.id)).where(ChatMessage.user_id == u.id)
            res_cnt = await session.execute(stmt_cnt)
            total_msgs = res_cnt.scalar() or 0

            # If no messages logged yet, check if user had inquiries
            last_text = last_msg.text if last_msg else None
            last_sender = last_msg.sender_type if last_msg else None
            last_time = last_msg.created_at.isoformat() if last_msg and last_msg.created_at else None

            if not last_msg:
                stmt_inq = (
                    select(Inquiry)
                    .where(Inquiry.user_id == u.id)
                    .order_by(Inquiry.created_at.desc())
                    .limit(1)
                )
                res_inq = await session.execute(stmt_inq)
                inq = res_inq.scalar_one_or_none()
                if inq:
                    last_text = inq.final_response or inq.ai_draft_response or inq.question_text
                    last_sender = "bot" if (inq.final_response or inq.ai_draft_response) else "user"
                    last_time = inq.created_at.isoformat() if inq.created_at else None

            dialogs.append(
                {
                    "user_id": u.id,
                    "telegram_id": u.telegram_id,
                    "full_name": u.full_name or "Mijoz",
                    "phone_number": u.phone_number,
                    "language": u.language,
                    "lead_status": u.lead_status,
                    "free_questions_left": u.free_questions_left,
                    "last_message": last_text or "Yozishma yo'q",
                    "last_sender": last_sender or "user",
                    "last_time": last_time or (u.created_at.isoformat() if u.created_at else None),
                    "total_messages": total_msgs,
                }
            )

        # Sort dialogs by last_time descending
        dialogs.sort(key=lambda d: d["last_time"] or "", reverse=True)
        return dialogs

    @classmethod
    async def send_lawyer_reply(
        cls,
        session: AsyncSession,
        bot: Bot,
        user_id: int,
        text: str,
    ) -> ChatMessage:
        """Lawyer sends a message directly to the client via Telegram Bot from the admin panel."""
        stmt = select(User).where(User.id == user_id)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Send via Telegram bot
        tg_msg = await bot.send_message(chat_id=user.telegram_id, text=text)

        # Log as lawyer message
        msg = await cls.log_message(
            session=session,
            user_id=user.id,
            telegram_id=user.telegram_id,
            sender_type="lawyer",
            text=text,
            telegram_message_id=tg_msg.message_id,
        )
        return msg

    @classmethod
    async def backfill_historical_inquiries(cls, session: AsyncSession) -> int:
        """Backfill existing inquiries into ChatMessage table if empty."""
        stmt_count = select(func.count(ChatMessage.id))
        res_count = await session.execute(stmt_count)
        if (res_count.scalar() or 0) > 0:
            return 0

        stmt_inqs = select(Inquiry, User.telegram_id).join(User, Inquiry.user_id == User.id)
        res_inqs = await session.execute(stmt_inqs)
        rows = res_inqs.all()

        count = 0
        for inq, tg_id in rows:
            # 1. User inquiry question
            if inq.question_text or inq.stt_transcript:
                session.add(
                    ChatMessage(
                        user_id=inq.user_id,
                        telegram_id=tg_id,
                        sender_type="user",
                        message_type="voice" if inq.stt_transcript else "text",
                        text=inq.question_text or inq.stt_transcript,
                        created_at=inq.created_at,
                    )
                )
                count += 1

            # 2. Bot/Lawyer response
            resp_text = inq.final_response or inq.ai_draft_response
            if resp_text:
                session.add(
                    ChatMessage(
                        user_id=inq.user_id,
                        telegram_id=tg_id,
                        sender_type="lawyer" if inq.status == "approved" else "bot",
                        message_type="text",
                        text=resp_text,
                        created_at=inq.answered_at or inq.created_at,
                    )
                )
                count += 1

        if count > 0:
            await session.commit()
            logger.info("Backfilled %d historical messages into ChatMessage table", count)
        return count

