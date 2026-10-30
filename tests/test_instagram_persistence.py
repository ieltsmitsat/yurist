"""Tests for Instagram database persistence (Phase 1)."""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.redis import InMemoryRedisClient
from app.db.base import Base
from app.db.models.chat_message import ChatMessage
from app.db.models.inquiry import Inquiry
from app.db.models.user import User
from app.services.instagram.persistence import InstagramPersistenceService
from app.services.instagram.service import InstagramAutomationService


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


@pytest.mark.asyncio
async def test_get_or_create_instagram_user(async_session: AsyncSession) -> None:
    # 1. Create first time
    user = await InstagramPersistenceService.get_or_create_user(
        session=async_session,
        instagram_id="ig_123456",
        username="law_client",
    )
    assert user.id is not None
    assert user.instagram_id == "ig_123456"
    assert user.platform == "instagram"
    assert user.telegram_id < 0
    assert user.lead_status == "new"

    # 2. Retrieve existing
    same_user = await InstagramPersistenceService.get_or_create_user(
        session=async_session,
        instagram_id="ig_123456",
    )
    assert same_user.id == user.id


@pytest.mark.asyncio
async def test_update_user_contact_and_merge(async_session: AsyncSession) -> None:
    # Existing Telegram user with phone
    existing_user = User(
        telegram_id=987654321,
        phone_number="+998901112233",
        full_name="Akmal Fayziyev",
        platform="telegram",
    )
    async_session.add(existing_user)
    await async_session.flush()

    # New Instagram user
    ig_user = await InstagramPersistenceService.get_or_create_user(
        session=async_session,
        instagram_id="ig_888999",
        username="akmal_ig",
    )

    # When phone is captured matching existing user
    merged = await InstagramPersistenceService.update_user_contact(
        session=async_session,
        user=ig_user,
        phone_number="+998901112233",
    )

    assert merged.id == existing_user.id
    assert merged.instagram_id == "ig_888999"
    assert merged.platform == "both"


@pytest.mark.asyncio
async def test_record_messages_and_inquiry(async_session: AsyncSession) -> None:
    user = await InstagramPersistenceService.get_or_create_user(
        session=async_session,
        instagram_id="ig_test_chat",
    )

    inbound = await InstagramPersistenceService.record_inbound_message(
        session=async_session,
        user=user,
        text="Aliment bo'yicha yordam kerak",
        instagram_message_id="mid.123",
    )
    assert inbound.channel == "instagram"
    assert inbound.sender_type == "user"
    assert inbound.text == "Aliment bo'yicha yordam kerak"

    outbound = await InstagramPersistenceService.record_outbound_message(
        session=async_session,
        user=user,
        text="Aliment stavkalari Oila kodeksiga muvofiq...",
        sender_type="bot",
    )
    assert outbound.channel == "instagram"
    assert outbound.sender_type == "bot"

    inquiry = await InstagramPersistenceService.record_inquiry(
        session=async_session,
        user=user,
        question_text=inbound.text or "",
        answer_text=outbound.text or "",
        category="oila",
        risk_level="medium",
        risk_score=50,
    )
    assert inquiry.channel == "instagram"
    assert inquiry.detected_category == "oila"
    assert inquiry.risk_level == "medium"
    assert inquiry.risk_score == 50


@pytest.mark.asyncio
async def test_full_direct_message_persistence_flow(async_session: AsyncSession) -> None:
    service = InstagramAutomationService()
    redis = InMemoryRedisClient()

    sender_id = "ig_user_flow_777"
    message_data = {
        "text": "Mening telefonim +998901234567. Shartnoma tuzish bo'yicha maslahat bering.",
        "mid": "msg_flow_001",
    }

    chunks = await service.handle_direct_message(
        sender_id=sender_id,
        message_data=message_data,
        redis_client=redis,
        db_session=async_session,
    )
    assert len(chunks) > 0

    # Verify user created in DB
    user_stmt = select(User).where(User.instagram_id == sender_id)
    res = await async_session.execute(user_stmt)
    user = res.scalar_one_or_none()
    assert user is not None
    assert user.phone_number == "+998901234567"
    assert user.lead_status == "contacted"
    assert user.platform == "instagram"

    # Verify chat messages recorded
    msg_stmt = select(ChatMessage).where(ChatMessage.user_id == user.id)
    msg_res = await async_session.execute(msg_stmt)
    messages = msg_res.scalars().all()
    assert len(messages) >= 2  # At least 1 inbound, 1 outbound
    assert any(m.sender_type == "user" for m in messages)
    assert any(m.sender_type == "bot" for m in messages)

    # Verify inquiry recorded
    inq_stmt = select(Inquiry).where(Inquiry.user_id == user.id)
    inq_res = await async_session.execute(inq_stmt)
    inquiries = inq_res.scalars().all()
    assert len(inquiries) == 1
    assert inquiries[0].channel == "instagram"
    assert inquiries[0].detected_category in ("biznes", "fuqarolik", "umumiy")
