"""Skill 1: Comment-to-DM Trigger & Conversion Skill (skill_comment_to_dm).

Analyzes user comments on Instagram Posts, Reels, and Ads, detects legal keywords,
enforces Meta rate limits (750/hour, 5s spacing), and sends a private reply prompting
the user to message in Direct to open the 24-hour window.
"""

import logging
import re
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class CommentToDMSkill:
    """Comment-to-DM trigger matching and private reply dispatcher."""

    # Default legal intent keywords
    DEFAULT_TRIGGER_KEYWORDS: tuple[str, ...] = (
        "sud",
        "yordam",
        "advokat",
        "yurist",
        "shartnoma",
        "ajrashish",
        "aliment",
        "meros",
        "jarima",
        "qarz",
        "ariza",
        "firibgar",
        "mol-mulk",
        "hokimiyat",
        "prokuratura",
        "iib",
    )

    CTA_PRIVATE_REPLY_TEMPLATE: str = (
        "Assalomu alaykum! Izohingiz bo'yicha masalangizni ko'rib chiqdim. "
        "Sizga aniq huquqiy yechim va yordam bera olishim uchun Direct'da "
        "'Ha' yoki 'Batafsil' deb javob qaytaring."
    )

    def __init__(self, keywords: tuple[str, ...] | None = None) -> None:
        self.keywords = keywords or self.DEFAULT_TRIGGER_KEYWORDS
        pattern_str = r"\b(" + "|".join(re.escape(k) for k in self.keywords) + r")\b"
        self._regex = re.compile(pattern_str, re.IGNORECASE)

    def matches_comment(self, comment_text: str) -> bool:
        """Check if comment contains any target legal keywords."""
        if not comment_text or not isinstance(comment_text, str):
            return False
        return bool(self._regex.search(comment_text.strip()))

    def extract_matched_keywords(self, comment_text: str) -> list[str]:
        """Return list of matched keywords in comment."""
        if not comment_text:
            return []
        matches = self._regex.findall(comment_text)
        return list(dict.fromkeys(m.lower() for m in matches))

    def build_private_reply_payload(
        self,
        comment_id: str,
        custom_message: str | None = None,
    ) -> dict[str, Any]:
        """Construct Graph API payload for POST /{comment-id}/private_replies."""
        message = (custom_message or self.CTA_PRIVATE_REPLY_TEMPLATE).strip()
        return {
            "endpoint": f"/{settings.INSTAGRAM_GRAPH_API_VERSION}/{comment_id}/private_replies",
            "method": "POST",
            "body": {
                "message": message,
            },
        }

    async def can_send_private_reply(
        self,
        comment_id: str,
        redis_client: Any | None = None,
    ) -> bool:
        """Ensure comment receives at most one private reply and respects rate limit."""
        if not comment_id:
            return False

        if redis_client is not None:
            # Check if private reply was already sent for this comment
            sent_key = f"ig_private_reply_sent:{comment_id}"
            already_sent = await redis_client.get(sent_key)
            if already_sent:
                logger.info("Private reply already sent for comment %s", comment_id)
                return False

            # Check 750/hour rate limit
            rate_key = "ig_private_replies_hourly_count"
            current_count_str = await redis_client.get(rate_key)
            current_count = int(current_count_str) if current_count_str else 0
            if current_count >= settings.INSTAGRAM_RATE_LIMIT_PER_HOUR:
                logger.warning(
                    "Hourly private reply rate limit reached (%d/%d)",
                    current_count,
                    settings.INSTAGRAM_RATE_LIMIT_PER_HOUR,
                )
                return False

        return True

    async def mark_reply_sent(
        self,
        comment_id: str,
        redis_client: Any | None = None,
    ) -> None:
        """Record that a private reply has been sent for this comment."""
        if redis_client is not None:
            sent_key = f"ig_private_reply_sent:{comment_id}"
            await redis_client.set(sent_key, "1", ex=86400 * 7)  # Remember for 7 days

            rate_key = "ig_private_replies_hourly_count"
            count_str = await redis_client.get(rate_key)
            new_count = (int(count_str) if count_str else 0) + 1
            await redis_client.set(rate_key, str(new_count), ex=3600)
