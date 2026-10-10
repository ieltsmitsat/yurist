"""Scheduler service for 24h and 48h automated lead nurturing and retargeting."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.inquiry import Inquiry
from app.db.models.user import User
from app.services.ai.llm_client import LLMService

logger = logging.getLogger(__name__)


class RetargetingSchedulerService:
    """Finds abandoned leads at 24h and 48h marks and generates personalized reminders."""

    def __init__(self, llm_service: LLMService | None = None) -> None:
        self.llm = llm_service or LLMService()

    async def get_leads_needing_followup(
        self,
        session: AsyncSession,
        hours: int = 24,
    ) -> list[tuple[User, Inquiry]]:
        """Find users who asked questions `hours` ago and haven't subscribed or booked."""
        now = datetime.now(UTC)
        start_time = now - timedelta(hours=hours + 1)
        end_time = now - timedelta(hours=hours)

        # Inquiries between [now - (hours+1), now - hours]
        stmt = (
            select(User, Inquiry)
            .join(Inquiry, Inquiry.user_id == User.id)
            .where(Inquiry.created_at >= start_time)
            .where(Inquiry.created_at <= end_time)
            .where(User.is_subscribed.is_(False))
        )
        res = await session.execute(stmt)
        return list(res.all())

    async def generate_followup_message(
        self,
        user: User,
        inquiry: Inquiry,
        hours: int = 24,
    ) -> str:
        """Generate a personalized follow-up message from the lawyer."""
        summary = inquiry.question_text or "yuridik murojaat"
        return await self.llm.generate_retargeting_followup(
            inquiry_summary=summary[:200],
            language=user.language,
            hours_passed=hours,
        )
