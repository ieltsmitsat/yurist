"""Skill 8: Meta Policy & Payload Safety Skill (skill_meta_policy_enforcer).

Guarantees compliance with Meta API restrictions:
1. Max 1,000 UTF-8 bytes per outbound message payload (safely chunked).
2. 30-second response SLA tracking.
3. 100 req/sec outbound rate-limiting buffer (Token Bucket).
"""

import logging
import time
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class MetaPolicyEnforcerSkill:
    """Enforces Meta Graph API constraints, message sizing, and SLA requirements."""

    MAX_UTF8_BYTES = 1000
    TARGET_SLA_SECONDS = 30.0
    MAX_REQUESTS_PER_SECOND = 100

    def __init__(self, max_bytes: int = MAX_UTF8_BYTES) -> None:
        self.max_bytes = max_bytes

    def split_message_if_exceeds_limit(self, text: str) -> list[str]:
        """Split message into parts if UTF-8 byte count exceeds 1,000 bytes."""
        if not text:
            return []

        encoded = text.encode("utf-8")
        if len(encoded) <= self.max_bytes:
            return [text]

        chunks: list[str] = []
        current_text = text

        while current_text:
            encoded_current = current_text.encode("utf-8")
            if len(encoded_current) <= self.max_bytes:
                chunks.append(current_text)
                break

            # Find a safe split position before max_bytes
            # Look for sentence boundary or whitespace
            target_slice = encoded_current[: self.max_bytes].decode("utf-8", errors="ignore")
            split_idx = -1

            # Try splitting by paragraph or sentence
            for delimiter in ("\n\n", "\n", ". ", "! ", "? ", "; ", " "):
                idx = target_slice.rfind(delimiter)
                if idx > 0:
                    split_idx = idx + len(delimiter)
                    break

            if split_idx <= 0:
                # Forced character cut if no delimiter found
                split_idx = len(target_slice)

            chunk = current_text[:split_idx].strip()
            if chunk:
                chunks.append(chunk)
            current_text = current_text[split_idx:].strip()

        return chunks

    @classmethod
    def check_sla_compliance(cls, start_time: float) -> tuple[bool, float]:
        """Calculate elapsed processing time and verify SLA compliance (< 30s)."""
        elapsed = time.time() - start_time
        is_compliant = elapsed <= cls.TARGET_SLA_SECONDS
        if not is_compliant:
            logger.warning(
                "Response SLA breached: took %.2fs (target < %.2fs)",
                elapsed,
                cls.TARGET_SLA_SECONDS,
            )
        return is_compliant, elapsed

    @classmethod
    async def acquire_rate_limit_slot(
        cls,
        redis_client: Any | None = None,
    ) -> bool:
        """Verify token bucket rate limit (100 req/sec) before sending outbound request."""
        if redis_client is None:
            return True

        current_second = int(datetime.now(UTC).timestamp())
        key = f"ig_outbound_rate_limit:{current_second}"

        count_str = await redis_client.get(key)
        current_count = int(count_str) if count_str else 0

        if current_count >= cls.MAX_REQUESTS_PER_SECOND:
            logger.warning("Outbound rate limit reached for second %d (100 req/s)", current_second)
            return False

        await redis_client.set(key, str(current_count + 1), ex=2)
        return True
