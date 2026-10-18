"""Inquiry message debouncer and aggregator service."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from aiogram import Bot
from aiogram.types import Message

from app.core.config import settings
from app.db.models.user import User

logger = logging.getLogger(__name__)


@dataclass
class BufferedMessage:
    """Represents a single message buffered for aggregation."""

    message: Message
    logged_msg_id: int
    text: str
    received_at: float = field(default_factory=time.time)


@dataclass
class UserInquiryQueue:
    """Queue of messages for a single user awaiting debounce flush."""

    user: User
    bot: Bot
    messages: list[BufferedMessage] = field(default_factory=list)
    timer_task: asyncio.Task[None] | None = None
    is_processing: bool = False


# Type of the async processor callback: (user: User, messages: list[BufferedMessage], bot: Bot) -> Awaitable[None]
InquiryProcessor = Callable[[User, list[BufferedMessage], Bot], Awaitable[None]]


class InquiryDebouncer:
    """Debounces and aggregates consecutive user messages before processing.

    When a user sends multiple messages in rapid succession (e.g. 'Salom' followed by
    their actual legal question), this service aggregates them into a single inquiry
    and dispatches a single response once the user stops typing.
    """

    def __init__(
        self,
        processor: InquiryProcessor | None = None,
        debounce_seconds: float | None = None,
    ) -> None:
        self.processor = processor
        self._debounce_seconds: float | None = debounce_seconds
        self._queues: dict[int, UserInquiryQueue] = {}

    @property
    def debounce_seconds(self) -> float:
        """Dynamic debounce delay in seconds (falls back to settings)."""
        if self._debounce_seconds is not None:
            return self._debounce_seconds
        return float(getattr(settings, "INQUIRY_DEBOUNCE_SECONDS", 3.0))

    @debounce_seconds.setter
    def debounce_seconds(self, value: float) -> None:
        self._debounce_seconds = float(value)

    def set_processor(self, processor: InquiryProcessor) -> None:
        """Register or update the async processor callback."""
        self.processor = processor

    async def add_message(
        self,
        user: User,
        message: Message,
        logged_msg_id: int,
        bot: Bot,
    ) -> None:
        """Add an incoming message to the user's debounce queue."""
        user_id = user.id
        queue = self._queues.get(user_id)
        if queue is None:
            queue = UserInquiryQueue(user=user, bot=bot)
            self._queues[user_id] = queue
        else:
            queue.user = user
            queue.bot = bot

        buffered = BufferedMessage(
            message=message,
            logged_msg_id=logged_msg_id,
            text=message.text or "",
        )
        queue.messages.append(buffered)

        # Cancel existing debounce timer if one is waiting
        if queue.timer_task and not queue.timer_task.done():
            queue.timer_task.cancel()
            queue.timer_task = None

        # If currently processing a previous batch, the new messages remain in queue
        # and will be scheduled automatically when current processing finishes.
        if queue.is_processing:
            logger.debug(
                "User #%d is currently processing; message buffered for next batch.",
                user_id,
            )
            return

        # Start new debounce timer
        queue.timer_task = asyncio.create_task(self._wait_and_flush(user_id))

    async def _wait_and_flush(self, user_id: int) -> None:
        """Wait for debounce window to elapse without new messages, then flush."""
        try:
            await asyncio.sleep(self.debounce_seconds)
        except asyncio.CancelledError:
            # Superseded by a newer message
            return

        await self.flush_user(user_id)

    async def flush_user(self, user_id: int) -> None:
        """Immediately process all pending messages for a user."""
        queue = self._queues.get(user_id)
        if not queue or not queue.messages:
            return

        if queue.is_processing:
            return

        if not self.processor:
            logger.error("No processor registered for InquiryDebouncer!")
            return

        queue.is_processing = True
        batch = list(queue.messages)
        queue.messages.clear()
        queue.timer_task = None
        user = queue.user
        bot = queue.bot

        try:
            await self.processor(user, batch, bot)
        except Exception as e:  # noqa: BLE001
            logger.error("Error processing aggregated inquiry for user #%d: %s", user_id, e)
        finally:
            queue.is_processing = False
            # If new messages arrived while processing, schedule the next batch
            if queue.messages:
                queue.timer_task = asyncio.create_task(self._wait_and_flush(user_id))
            else:
                self._queues.pop(user_id, None)

    def cancel_user(self, user_id: int) -> None:
        """Cancel pending debounce and clear queue for a user."""
        queue = self._queues.pop(user_id, None)
        if queue and queue.timer_task and not queue.timer_task.done():
            queue.timer_task.cancel()

    def cancel_all(self) -> None:
        """Cancel all pending debounce timers across all users."""
        for q in self._queues.values():
            if q.timer_task and not q.timer_task.done():
                q.timer_task.cancel()
        self._queues.clear()


# Global debouncer instance
inquiry_debouncer = InquiryDebouncer()
