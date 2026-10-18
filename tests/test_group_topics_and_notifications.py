"""Tests for Telegram supergroup forum topics configuration and group notification service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.system_access import SystemAccess
from app.db.models.user import User
from app.services.access_service import AccessService
from app.services.group_notification_service import GroupNotificationService


@pytest.mark.asyncio
async def test_notify_new_lead_success():
    """Verify that notify_new_lead sends message to configured lead topics."""
    bot = AsyncMock()
    session = AsyncMock()

    user = MagicMock(spec=User)
    user.telegram_id = 999888
    user.full_name = "Olim Olimov"
    user.phone_number = "+998901234567"
    user.language = "uz"

    with patch.object(
        AccessService,
        "get_topic_destinations",
        AsyncMock(return_value=[(-100111222, 45), (-100333444, 99)]),
    ):
        sent = await GroupNotificationService.notify_new_lead(
            bot=bot,
            session=session,
            user=user,
            purpose="Meros masalasida yordam kerak",
        )

        assert sent == 2
        assert bot.send_message.call_count == 2

        # Check call arguments
        call1 = bot.send_message.call_args_list[0]
        assert call1.kwargs["chat_id"] == -100111222
        assert call1.kwargs["message_thread_id"] == 45
        assert "Olim Olimov" in call1.kwargs["text"]
        assert "+998901234567" in call1.kwargs["text"]
        assert "Meros masalasida yordam kerak" in call1.kwargs["text"]


@pytest.mark.asyncio
async def test_notify_new_lead_no_destinations():
    """When no group has lead_topic_id configured, no message should be sent."""
    bot = AsyncMock()
    session = AsyncMock()
    user = MagicMock(spec=User)

    with patch.object(AccessService, "get_topic_destinations", AsyncMock(return_value=[])):
        sent = await GroupNotificationService.notify_new_lead(
            bot=bot,
            session=session,
            user=user,
            purpose="Savol matni",
        )
        assert sent == 0
        bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_notify_payment_receipt_success():
    """Verify that payment receipt photo is sent to configured payment topics."""
    bot = AsyncMock()
    session = AsyncMock()

    user = MagicMock(spec=User)
    user.telegram_id = 777666
    user.full_name = "Zulayho Karimova"
    user.phone_number = "+998912345678"

    with patch.object(
        AccessService,
        "get_topic_destinations",
        AsyncMock(return_value=[(-100555666, 12)]),
    ):
        sent = await GroupNotificationService.notify_payment_receipt(
            bot=bot,
            session=session,
            user=user,
            photo_file_id="tg_photo_file_id_xyz",
            problem_summary="Da'vo arizasi xizmati",
            tx_id=88,
        )

        assert sent == 1
        bot.send_photo.assert_called_once()
        args = bot.send_photo.call_args.kwargs
        assert args["chat_id"] == -100555666
        assert args["message_thread_id"] == 12
        assert args["photo"] == "tg_photo_file_id_xyz"
        assert "Zulayho Karimova" in args["caption"]
        assert "#88" in args["caption"]


@pytest.mark.asyncio
async def test_notify_contact_request_success():
    """Verify that contact request is sent to configured contact topics."""
    bot = AsyncMock()
    session = AsyncMock()

    user = MagicMock(spec=User)
    user.telegram_id = 555444
    user.full_name = "Jasur Rustamov"
    user.phone_number = "+998933332211"

    with patch.object(
        AccessService,
        "get_topic_destinations",
        AsyncMock(return_value=[(-100777888, 33)]),
    ):
        sent = await GroupNotificationService.notify_contact_request(
            bot=bot,
            session=session,
            user=user,
            service_title="Yuridik audit xizmati",
            problem_summary="Kompaniya shartnomasi tekshiruvi",
        )

        assert sent == 1
        bot.send_message.assert_called_once()
        args = bot.send_message.call_args.kwargs
        assert args["chat_id"] == -100777888
        assert args["message_thread_id"] == 33
        assert "Jasur Rustamov" in args["text"]
        assert "+998933332211" in args["text"]
        assert "Yuridik audit xizmati" in args["text"]


@pytest.mark.asyncio
async def test_system_access_create_and_update_with_topics():
    """Verify AccessService creates and updates topic IDs properly with dedicated engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[SystemAccess.__table__])

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Create group with topic IDs
        group = await AccessService.create(
            session=session,
            telegram_id=-1009999991,
            name="Test Hub Guruhi",
            role="group",
            description="Boshqaruv forumi",
            lead_topic_id=101,
            contact_topic_id=102,
            payment_topic_id=103,
        )

        assert group.lead_topic_id == 101
        assert group.contact_topic_id == 102
        assert group.payment_topic_id == 103

        # Test get_topic_destinations
        lead_dests = await AccessService.get_topic_destinations(session, "lead")
        assert (-1009999991, 101) in lead_dests

        contact_dests = await AccessService.get_topic_destinations(session, "contact")
        assert (-1009999991, 102) in contact_dests

        payment_dests = await AccessService.get_topic_destinations(session, "payment")
        assert (-1009999991, 103) in payment_dests

        # Update: clear payment topic ID
        updated = await AccessService.update(
            session=session,
            access_id=group.id,
            payment_topic_id=None,
        )
        assert updated is not None
        assert updated.payment_topic_id is None

        # Now payment_dests should not include this group
        new_payment_dests = await AccessService.get_topic_destinations(session, "payment")
        assert (-1009999991, 103) not in new_payment_dests

    await engine.dispose()
