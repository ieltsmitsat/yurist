"""Skill 7: Human Agent Handoff & Manual Takeover Skill (skill_human_handoff).

Controls lawyer takeover pause (30-minute freeze in Redis) and handles Meta's
HUMAN_AGENT message tag for responses beyond the 24-hour standard window (up to 7 days).
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class HumanAgentHandoffSkill:
    """Manages lawyer manual takeover state and Meta message tagging."""

    AI_PAUSE_PREFIX = "ig_ai_pause"
    DEFAULT_PAUSE_SECONDS = 1800  # 30 minutes
    SEVEN_DAYS_SECONDS = 7 * 86400

    @classmethod
    def _make_pause_key(cls, chat_id: str) -> str:
        return f"{cls.AI_PAUSE_PREFIX}:{chat_id}"

    @classmethod
    async def set_lawyer_takeover(
        cls,
        chat_id: str,
        redis_client: Any,
        pause_seconds: int = DEFAULT_PAUSE_SECONDS,
    ) -> None:
        """Pause AI responses for 30 minutes because lawyer intervened."""
        key = cls._make_pause_key(chat_id)
        await redis_client.set(key, "1", ex=pause_seconds)
        logger.info(
            "Lawyer takeover initiated. AI paused for Instagram chat %s for %d seconds",
            chat_id,
            pause_seconds,
        )

    @classmethod
    async def is_ai_paused(
        cls,
        chat_id: str,
        redis_client: Any,
    ) -> bool:
        """Check if AI is currently muted for this chat."""
        if redis_client is None:
            return False
        key = cls._make_pause_key(chat_id)
        val = await redis_client.get(key)
        return val is not None

    @classmethod
    async def resume_ai(
        cls,
        chat_id: str,
        redis_client: Any,
    ) -> None:
        """Manually resume AI responses for a chat."""
        if redis_client is not None:
            key = cls._make_pause_key(chat_id)
            await redis_client.delete(key)
            logger.info("AI manually resumed for Instagram chat %s", chat_id)

    @classmethod
    def should_use_human_agent_tag(
        cls,
        last_inbound_timestamp: float,
        current_timestamp: float,
    ) -> bool:
        """Determine if message requires HUMAN_AGENT message_tag (24h < elapsed <= 7 days)."""
        elapsed = current_timestamp - last_inbound_timestamp
        # Standard window is <= 24h (86400s)
        # Human agent tag applies between 24h and 7 days
        return 86400 < elapsed <= cls.SEVEN_DAYS_SECONDS

    @classmethod
    def build_outbound_payload(
        cls,
        recipient_id: str,
        text: str,
        use_human_agent_tag: bool = False,
    ) -> dict[str, Any]:
        """Construct standard or Human Agent tagged outbound message payload."""
        payload: dict[str, Any] = {
            "recipient": {"id": recipient_id},
            "message": {"text": text},
        }
        if use_human_agent_tag:
            payload["messaging_type"] = "MESSAGE_TAG"
            payload["tag"] = "HUMAN_AGENT"
        else:
            payload["messaging_type"] = "RESPONSE"
        return payload
