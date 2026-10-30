"""Database persistence layer for Instagram DM Automation.

Handles creating/finding omnichannel users, recording inquiries, storing chat messages,
and linking user profiles by phone number.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat_message import ChatMessage
from app.db.models.inquiry import Inquiry, InquiryStatus
from app.db.models.user import User

logger = logging.getLogger(__name__)


class InstagramPersistenceService:
    """Manages database transactions for Instagram leads, chats, and inquiries."""

    @staticmethod
    def _generate_synthetic_telegram_id(instagram_id: str) -> int:
        """Generate a negative unique 64-bit int ID for Instagram users without Telegram."""
        if instagram_id.isdigit():
            val = int(instagram_id)
            if val < 2**62:
                return -val
        return -(abs(hash(instagram_id)) % (2**62))

    @classmethod
    async def get_or_create_user(
        cls,
        session: AsyncSession,
        instagram_id: str,
        full_name: str | None = None,
        username: str | None = None,
    ) -> User:
        """Find user by instagram_id or create new Instagram user."""
        stmt = select(User).where(User.instagram_id == instagram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is not None:
            if username and not user.instagram_username:
                user.instagram_username = username
            if full_name and not user.full_name:
                user.full_name = full_name
            return user

        synthetic_tg_id = cls._generate_synthetic_telegram_id(instagram_id)
        user = User(
            telegram_id=synthetic_tg_id,
            instagram_id=instagram_id,
            instagram_username=username,
            full_name=full_name or f"Instagram User {instagram_id[-4:]}",
            platform="instagram",
            lead_status="new",
            free_questions_left=3,
        )
        session.add(user)
        await session.flush()
        logger.info("Created new Instagram lead in DB (ID: %d, IGSID: %s)", user.id, instagram_id)
        return user

    @classmethod
    async def update_user_contact(
        cls,
        session: AsyncSession,
        user: User,
        phone_number: str,
    ) -> User:
        """Save phone number and upgrade lead status to contacted, merging if phone exists."""
        clean_phone = phone_number.strip()
        user.phone_number = clean_phone
        if user.lead_status == "new":
            user.lead_status = "contacted"

        # Check if another user profile exists with this exact phone number
        stmt = select(User).where(User.phone_number == clean_phone, User.id != user.id)
        res = await session.execute(stmt)
        existing_profile = res.scalar_one_or_none()

        if existing_profile is not None:
            # Merge Instagram identity into primary profile
            existing_profile.instagram_id = user.instagram_id
            existing_profile.instagram_username = (
                user.instagram_username or existing_profile.instagram_username
            )
            existing_profile.platform = "both"
            logger.info(
                "Merged Instagram user %s into existing User profile %d via phone %s",
                user.instagram_id,
                existing_profile.id,
                clean_phone,
            )
            return existing_profile

        return user

    @classmethod
    async def record_inbound_message(
        cls,
        session: AsyncSession,
        user: User,
        text: str,
        message_type: str = "text",
        media_url: str | None = None,
        instagram_message_id: str | None = None,
    ) -> ChatMessage:
        """Store incoming user message in chat_messages table."""
        msg = ChatMessage(
            user_id=user.id,
            telegram_id=user.telegram_id,
            sender_type="user",
            message_type=message_type,
            text=text,
            media_url=media_url,
            instagram_message_id=instagram_message_id,
            channel="instagram",
        )
        session.add(msg)
        await session.flush()
        return msg

    @classmethod
    async def record_outbound_message(
        cls,
        session: AsyncSession,
        user: User,
        text: str,
        sender_type: str = "bot",
        message_type: str = "text",
    ) -> ChatMessage:
        """Store outgoing bot/lawyer message in chat_messages table."""
        msg = ChatMessage(
            user_id=user.id,
            telegram_id=user.telegram_id,
            sender_type=sender_type,
            message_type=message_type,
            text=text,
            channel="instagram",
        )
        session.add(msg)
        await session.flush()
        return msg

    @classmethod
    async def record_inquiry(
        cls,
        session: AsyncSession,
        user: User,
        question_text: str,
        answer_text: str,
        category: str | None = None,
        risk_level: str | None = None,
        risk_score: int | None = None,
    ) -> Inquiry:
        """Store question, response, category, and risk level in inquiries table."""
        inquiry = Inquiry(
            user_id=user.id,
            channel="instagram",
            question_text=question_text,
            final_response=answer_text,
            detected_category=category,
            risk_level=risk_level,
            risk_score=risk_score,
            status=InquiryStatus.ANSWERED.value,
            answered_at=datetime.now(UTC),
        )
        session.add(inquiry)
        await session.flush()
        return inquiry
