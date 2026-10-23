"""Tests for mandatory channels subscription model, API endpoints, and bot service."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import Message
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.main import create_app
from app.db.base import Base
from app.db.models.mandatory_channel import MandatoryChannel
from app.db.models.user import User
from app.db.session import get_db_session
from app.services.subscription_service import SubscriptionService

api_app = create_app()

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


api_app.dependency_overrides[get_db_session] = override_get_db


@pytest.fixture(autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        tables = [
            User.__table__,
            MandatoryChannel.__table__,
        ]
        await conn.run_sync(Base.metadata.create_all, tables=tables)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all, tables=tables)


@pytest.mark.asyncio
async def test_mandatory_channel_crud_api() -> None:
    """Test full CRUD operations on mandatory channels via FastAPI test client."""
    async with AsyncClient(
        transport=ASGITransport(app=api_app), base_url="http://test"
    ) as client:
        # 1. Create channel
        res = await client.post(
            "/api/v1/channels",
            json={
                "title": "Adliya Yangiliklari",
                "chat_id": "@adliya_yangiliklari",
                "url": "https://t.me/adliya_yangiliklari",
                "order": 1,
                "is_active": True,
            },
        )
        assert res.status_code == 201
        data = res.json()
        channel_id = data["id"]
        assert data["title"] == "Adliya Yangiliklari"
        assert data["chat_id"] == "@adliya_yangiliklari"
        assert data["is_active"] is True

        # 2. List channels
        res = await client.get("/api/v1/channels")
        assert res.status_code == 200
        items = res.json()
        assert len(items) >= 1
        assert any(i["id"] == channel_id for i in items)

        # 3. Update channel
        res = await client.put(
            f"/api/v1/channels/{channel_id}",
            json={"title": "Adliya Yangiliklari Rasmiy"},
        )
        assert res.status_code == 200
        assert res.json()["title"] == "Adliya Yangiliklari Rasmiy"

        # 4. Toggle active status
        res = await client.patch(f"/api/v1/channels/{channel_id}/toggle")
        assert res.status_code == 200
        assert res.json()["is_active"] is False

        # 5. Delete channel
        res = await client.delete(f"/api/v1/channels/{channel_id}")
        assert res.status_code == 200
        assert res.json()["ok"] is True

        # Verify not found
        res = await client.delete(f"/api/v1/channels/{channel_id}")
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_subscription_service_check_and_ui() -> None:
    """Test SubscriptionService logic for subscribed and unsubscribed users."""
    async with TestingSessionLocal() as session:
        # Seed 2 active channels
        ch1 = MandatoryChannel(
            title="Kanal 1",
            chat_id="@kanal1",
            url="https://t.me/kanal1",
            order=1,
            is_active=True,
        )
        ch2 = MandatoryChannel(
            title="Guruh 2",
            chat_id="-100999888",
            url="https://t.me/guruh2",
            order=2,
            is_active=True,
        )
        session.add_all([ch1, ch2])
        await session.commit()

        bot_mock = MagicMock(spec=Bot)

        # 1. User is member of ch1 but left ch2
        async def fake_get_chat_member(chat_id: int | str, user_id: int):
            if chat_id == "@kanal1":
                return MagicMock(status=ChatMemberStatus.MEMBER)
            return MagicMock(status=ChatMemberStatus.LEFT)

        bot_mock.get_chat_member = AsyncMock(side_effect=fake_get_chat_member)

        is_sub, unsubs = await SubscriptionService.check_user_subscribed_all(
            bot=bot_mock,
            user_id=12345,
            session=session,
            bypass_cache=True,
        )
        assert is_sub is False
        assert len(unsubs) == 1
        assert unsubs[0].title == "Guruh 2"

        # UI generation tests
        msg_uz = SubscriptionService.build_subscription_message(unsubs, "uz")
        assert "Hurmatli foydalanuvchi" in msg_uz
        assert "https://t.me/guruh2" in msg_uz

        msg_ru = SubscriptionService.build_subscription_message(unsubs, "ru")
        assert "Уважаемый пользователь" in msg_ru

        kb = SubscriptionService.build_subscription_keyboard(unsubs, "uz")
        assert len(kb.inline_keyboard) == 2  # 1 channel button + 1 check button
        assert kb.inline_keyboard[0][0].url == "https://t.me/guruh2"
        assert kb.inline_keyboard[1][0].callback_data == "check_mandatory_sub"

        # 2. User is member of all channels
        async def fake_all_member(chat_id: int | str, user_id: int):
            return MagicMock(status=ChatMemberStatus.MEMBER)

        bot_mock.get_chat_member = AsyncMock(side_effect=fake_all_member)

        is_all_sub, no_unsubs = await SubscriptionService.check_user_subscribed_all(
            bot=bot_mock,
            user_id=12345,
            session=session,
            bypass_cache=True,
        )
        assert is_all_sub is True
        assert len(no_unsubs) == 0


@pytest.mark.asyncio
async def test_mandatory_sub_middleware_interception() -> None:
    """Test that MandatorySubscriptionMiddleware intercepts unsubscribed users and passes subscribed ones."""
    from app.bot.middlewares.mandatory_sub_middleware import MandatorySubscriptionMiddleware

    middleware = MandatorySubscriptionMiddleware()

    async with TestingSessionLocal() as session:
        # User in DB
        user = User(telegram_id=987654, full_name="Test User", language="uz", lead_status="new")
        session.add(user)
        await session.commit()

        # Add active channel
        ch = MandatoryChannel(title="Kanal", chat_id="@kanall", url="https://t.me/kanall", is_active=True)
        session.add(ch)
        await session.commit()

        bot_mock = MagicMock(spec=Bot)
        bot_mock.get_chat_member = AsyncMock(
            return_value=MagicMock(status=ChatMemberStatus.LEFT)
        )

        message_mock = MagicMock(spec=Message)
        message_mock.business_connection_id = None
        user_tg = MagicMock()
        user_tg.id = 987654
        user_tg.language_code = "uz"
        message_mock.from_user = user_tg
        message_mock.answer = AsyncMock()

        handler_called = False

        async def fake_handler(event, data):
            nonlocal handler_called
            handler_called = True
            return "OK"

        data = {
            "event_from_user": user_tg,
            "user": user,
            "session": session,
            "bot": bot_mock,
            "is_business": False,
        }

        # Execute middleware on unsubscribed user
        result = await middleware(fake_handler, message_mock, data)

        assert result is None
        assert handler_called is False
        assert message_mock.answer.called
        call_args = message_mock.answer.call_args[0][0]
        assert "Hurmatli foydalanuvchi" in call_args
