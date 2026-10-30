"""Tests for Phase 3-6: Advanced Triggers, Window Watcher, Admin Chat & Handoff, and Omnichannel Telegram Alerting."""

import time
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.user import User
from app.services.chat_service import ChatService
from app.services.group_notification_service import GroupNotificationService
from app.services.instagram.service import InstagramAutomationService
from app.services.instagram.triggers import StoryAndAdsTriggerSkill
from app.services.instagram.window_watcher import InstagramWindowWatcherService


@pytest.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide isolated in-memory SQLite database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


class MockRedis:
    """Mock Redis client for testing."""

    def __init__(self) -> None:
        self.store: dict[str, Any] = {}

    async def get(self, key: str) -> Any:
        return self.store.get(key)

    async def set(self, key: str, value: Any, ex: int | None = None) -> bool:
        self.store[key] = value
        return True

    async def delete(self, key: str) -> int:
        if key in self.store:
            del self.store[key]
            return 1
        return 0


# ==========================================
# 1. Phase 3: Advanced Triggers Skill Tests
# ==========================================


def test_story_mention_detection() -> None:
    """Test detection of Instagram Story mentions via attachments and flags."""
    # Attachment-based mention
    mention_msg = {
        "mid": "m_123",
        "attachments": [{"type": "story_mention", "payload": {"url": "https://instagram.com/story/1"}}],
    }
    assert StoryAndAdsTriggerSkill.is_story_mention(mention_msg) is True

    # Flag-based mention
    flag_msg = {"mid": "m_124", "story_mention": True}
    assert StoryAndAdsTriggerSkill.is_story_mention(flag_msg) is True

    # Normal text message
    text_msg = {"mid": "m_125", "text": "Salom"}
    assert StoryAndAdsTriggerSkill.is_story_mention(text_msg) is False


def test_story_reply_detection() -> None:
    """Test detection of Instagram Story replies."""
    reply_msg = {
        "mid": "m_126",
        "text": "Bu qancha turadi?",
        "reply_to": {"story": {"id": "story_999"}},
    }
    assert StoryAndAdsTriggerSkill.is_story_reply(reply_msg) is True

    normal_msg = {"mid": "m_127", "text": "Savolim bor edi"}
    assert StoryAndAdsTriggerSkill.is_story_reply(normal_msg) is False


def test_ad_referral_extraction() -> None:
    """Test Click-to-Direct ad referral extraction and greeting generation."""
    msg_with_ad = {
        "mid": "m_128",
        "referral": {
            "source": "ADS",
            "ad_id": "ad_888",
            "ref": "feed_ad_campaign",
            "ad_title": "Bepul yuridik tahlil",
        },
    }
    referral = StoryAndAdsTriggerSkill.extract_ad_referral(msg_with_ad)
    assert referral is not None
    assert referral["source"] == "ADS"
    assert referral["ad_id"] == "ad_888"
    assert referral["ad_title"] == "Bepul yuridik tahlil"

    greeting = StoryAndAdsTriggerSkill.get_ad_referral_greeting("Bepul yuridik tahlil")
    assert "Bepul yuridik tahlil" in greeting
    assert "reklamamiz orqali murojaat qilganingiz uchun tashakkur" in greeting


# ==========================================
# 2. Phase 4: 24h Window Watcher Tests
# ==========================================


@pytest.mark.asyncio
async def test_window_watcher_sends_warning(async_session: AsyncSession) -> None:
    """Test that InstagramWindowWatcherService sends a warning 2 hours before window expiration."""
    redis = MockRedis()
    ig_id = "ig_user_watcher_101"

    # Create an Instagram lead in the DB without phone number
    user = User(
        telegram_id=-101101,
        full_name="Tester Watcher",
        platform="instagram",
        instagram_id=ig_id,
        phone_number=None,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    # Set last inbound activity to 22.5 hours ago (eligible for 2-hour closing warning)
    now = time.time()
    last_inbound = now - (22.5 * 3600)
    await redis.set(f"ig_user_last_inbound:{ig_id}", str(last_inbound))

    sent_messages: list[tuple[str, str]] = []

    async def mock_sender(recipient: str, text: str) -> bool:
        sent_messages.append((recipient, text))
        return True

    warnings_sent = await InstagramWindowWatcherService.run_window_check(
        session=async_session,
        redis_client=redis,
        custom_sender=mock_sender,
    )

    assert warnings_sent == 1
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == ig_id
    assert "24 soatlik bepul muloqot oynasi" in sent_messages[0][1]

    # Verify warning flag was set so it won't send again
    assert await redis.get(f"{InstagramWindowWatcherService.WARNING_KEY_PREFIX}:{ig_id}") == "1"

    # Second run should send 0 warnings because it was already sent
    warnings_sent_again = await InstagramWindowWatcherService.run_window_check(
        session=async_session,
        redis_client=redis,
        custom_sender=mock_sender,
    )
    assert warnings_sent_again == 0


# ==========================================
# 3. Phase 5: Web Admin Live Chat & Handoff
# ==========================================


@pytest.mark.asyncio
async def test_lawyer_reply_omnichannel_to_instagram(async_session: AsyncSession) -> None:
    """Test that ChatService.send_lawyer_reply routes to Instagram and sets 30-min AI pause."""
    redis = MockRedis()
    ig_id = "ig_lawyer_reply_202"

    user = User(
        telegram_id=-202202,
        full_name="Instagram Lead 202",
        platform="instagram",
        instagram_id=ig_id,
        phone_number="+998901112233",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    # Mock Bot (should NOT be called for Instagram-only user)
    mock_bot = AsyncMock()

    with patch.object(InstagramAutomationService, "_send_meta_request", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        msg = await ChatService.send_lawyer_reply(
            session=async_session,
            bot=mock_bot,
            user_id=user.id,
            text="Assalomu alaykum, men advokatman. Da'vo arizasini tayyorlashga kirishdik.",
            redis_client=redis,
        )

        assert msg is not None
        assert msg.sender_type == "lawyer"
        assert "advokatman" in (msg.text or "")
        mock_bot.send_message.assert_not_called()

        # Check that 30-min AI takeover pause was set in Redis
        is_paused = await redis.get(f"ig_ai_pause:{ig_id}")
        assert is_paused == "1"


# ==========================================
# 4. Phase 6: Omnichannel Telegram Alerting
# ==========================================


@pytest.mark.asyncio
async def test_telegram_lead_and_sos_alerts(async_session: AsyncSession) -> None:
    """Test dispatch of Instagram lead contacts and SOS emergency alerts to Telegram topics."""
    user = User(
        telegram_id=-303303,
        full_name="Sherzodbek",
        platform="instagram",
        instagram_id="ig_sherzod_303",
        instagram_username="sherzod_law",
        phone_number="+998901234567",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    mock_bot = AsyncMock()

    # Test Lead notification with fallback to admin group
    with patch("app.services.group_notification_service.settings.ADMIN_GROUP_ID", 123456789):
        sent_count = await GroupNotificationService.notify_instagram_lead(
            bot=mock_bot,
            session=async_session,
            user=user,
            message_text="Sudga da'vo ariza bermoqchiman",
        )
        assert sent_count == 1
        assert mock_bot.send_message.called
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 123456789
        assert "[INSTAGRAM DIRECT] YANGI LID KONTAKTI" in call_kwargs["text"]
        assert "+998901234567" in call_kwargs["text"]
        assert "@sherzod_law" in call_kwargs["text"]

    mock_bot.reset_mock()

    # Test SOS notification
    with patch("app.services.group_notification_service.settings.ADMIN_GROUP_ID", 123456789):
        sos_count = await GroupNotificationService.notify_instagram_sos(
            bot=mock_bot,
            session=async_session,
            user=user,
            question="Meni ichki ishlar bo'limida noqonuniy ushlab turishibdi!",
            risk_score=95,
            risk_level="critical",
        )
        assert sos_count == 1
        assert mock_bot.send_message.called
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert "[INSTAGRAM] SHOSHILINCH SOS OGOHLANTIRISH" in call_kwargs["text"]
        assert "95/100" in call_kwargs["text"]
        assert "ushlab turishibdi" in call_kwargs["text"]


# ==========================================
# 5. Phase 5: Admin Endpoints API Tests
# ==========================================


@pytest.mark.asyncio
async def test_admin_instagram_pause_endpoint() -> None:
    """Test POST /api/v1/instagram/pause toggles AI pause state."""
    from app.api.v1.instagram import InstagramPauseRequest, toggle_instagram_ai_pause

    redis = MockRedis()
    ig_id = "ig_user_pause_505"

    # 1. Pause
    req_pause = InstagramPauseRequest(instagram_id=ig_id, pause=True, duration_minutes=30)
    res_pause = await toggle_instagram_ai_pause(payload=req_pause, redis_client=redis)
    assert res_pause["ok"] is True
    assert res_pause["paused"] is True
    assert await redis.get(f"ig_ai_pause:{ig_id}") == "1"

    # 2. Resume
    req_resume = InstagramPauseRequest(instagram_id=ig_id, pause=False)
    res_resume = await toggle_instagram_ai_pause(payload=req_resume, redis_client=redis)
    assert res_resume["ok"] is True
    assert res_resume["paused"] is False
    assert await redis.get(f"ig_ai_pause:{ig_id}") is None


@pytest.mark.asyncio
async def test_admin_instagram_send_endpoint(async_session: AsyncSession) -> None:
    """Test POST /api/v1/instagram/send dispatches lawyer reply and records message."""
    from app.api.v1.instagram import InstagramSendRequest, send_manual_instagram_reply

    redis = MockRedis()
    ig_id = "ig_user_send_606"

    user = User(
        telegram_id=-606606,
        full_name="Direct Lead",
        platform="instagram",
        instagram_id=ig_id,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    req = InstagramSendRequest(instagram_id=ig_id, text="Hujjatlaringizni ko'rib chiqdik.")

    with patch.object(InstagramAutomationService, "_send_meta_request", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        res = await send_manual_instagram_reply(payload=req, redis_client=redis, db_session=async_session)
        assert res["ok"] is True
        assert res["instagram_id"] == ig_id
        # AI should be paused for this lead
        assert await redis.get(f"ig_ai_pause:{ig_id}") == "1"

