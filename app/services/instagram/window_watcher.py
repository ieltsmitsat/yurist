"""Background worker monitoring 24-hour Instagram messaging windows (Phase 4).

Dispatches closing warning messages to leads 2 hours before window expiration (at 22h mark)
and flags expired windows to prevent Meta API Error 10 out-of-window violations.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.user import User
from app.services.instagram.contact_capture import ContactCapture24hSkill
from app.services.instagram.persistence import InstagramPersistenceService

logger = logging.getLogger(__name__)


class InstagramWindowWatcherService:
    """Monitors active Instagram conversations and executes re-engagement before window closure."""

    WARNING_KEY_PREFIX = "ig_closing_warning_sent"

    @classmethod
    async def run_window_check(
        cls,
        session: AsyncSession,
        redis_client: Any | None = None,
        custom_sender: Any | None = None,
    ) -> int:
        """Scan active Instagram users and send 2-hour warning to eligible leads.

        Returns the number of warnings sent.
        """
        now = datetime.now(UTC).timestamp()
        stmt = (
            select(User)
            .where(User.platform.in_(["instagram", "both"]))
            .where(User.instagram_id.is_not(None))
        )
        res = await session.execute(stmt)
        users = res.scalars().all()

        warnings_sent = 0
        for user in users:
            ig_id = user.instagram_id
            if not ig_id:
                continue

            last_inbound = await ContactCapture24hSkill.get_last_inbound_timestamp(
                ig_user_id=ig_id,
                redis_client=redis_client,
            )
            if not last_inbound:
                continue

            # Check if warning was already sent
            warning_sent_flag = False
            if redis_client is not None:
                sent_key = f"{cls.WARNING_KEY_PREFIX}:{ig_id}"
                warning_sent_flag = await redis_client.get(sent_key) is not None

            should_warn = ContactCapture24hSkill.should_send_closing_warning(
                last_inbound_timestamp=last_inbound,
                warning_already_sent=warning_sent_flag,
            )

            # Only send warning if phone number is not yet collected
            if should_warn and not user.phone_number:
                warning_text = ContactCapture24hSkill.WINDOW_EXPIRING_WARNING
                success = False

                if custom_sender is not None:
                    success = await custom_sender(ig_id, warning_text)
                else:
                    success = await cls._send_outbound_warning(ig_id, warning_text)

                if success:
                    warnings_sent += 1
                    # Record in chat_messages table
                    await InstagramPersistenceService.record_outbound_message(
                        session=session,
                        user=user,
                        text=warning_text,
                        sender_type="bot",
                    )
                    await session.commit()

                    if redis_client is not None:
                        sent_key = f"{cls.WARNING_KEY_PREFIX}:{ig_id}"
                        # Remember warning was sent for 24h
                        await redis_client.set(sent_key, "1", ex=86400)
                        logger.info("Sent 24h window expiration warning to Instagram lead %s", ig_id)

            # If 24h expired, mark expired flag in Redis
            elapsed_hours = (now - last_inbound) / 3600.0
            if elapsed_hours >= 24.0 and redis_client is not None:
                await redis_client.set(f"ig_window_expired:{ig_id}", "1", ex=86400 * 7)

        return warnings_sent

    @classmethod
    async def _send_outbound_warning(cls, recipient_id: str, text: str) -> bool:
        """Send message via Meta Graph API."""
        if not settings.INSTAGRAM_ACCESS_TOKEN:
            logger.debug("INSTAGRAM_ACCESS_TOKEN not set; skipping live outbound warning")
            return True

        import httpx

        url = f"https://graph.facebook.com/{settings.INSTAGRAM_GRAPH_API_VERSION}/me/messages"
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text},
            "messaging_type": "RESPONSE",
        }
        headers = {
            "Authorization": f"Bearer {settings.INSTAGRAM_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(url, json=payload, headers=headers)
                return r.status_code in (200, 201)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed sending Instagram window warning to %s: %s", recipient_id, e)
            return False
