"""Tests for business services: UserService, ReferralService, PaymentService."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.db.models.appointment import Appointment
from app.db.models.attachment import Attachment
from app.db.models.inquiry import Inquiry
from app.db.models.org_settings import OrgSettings
from app.db.models.service import Service
from app.db.models.sos import SOSRequest
from app.db.models.system_access import SystemAccess
from app.db.models.transaction import Transaction
from app.db.models.user import User
from app.services.org_settings_service import OrgSettingsService
from app.services.payment_service import PaymentService
from app.services.referral_service import ReferralService
from app.services.user_service import UserService

# SQLite async engine for tests
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        # Create tables (excluding LegalChunk which uses pgvector)
        tables = [
            User.__table__,
            Service.__table__,
            Inquiry.__table__,
            Appointment.__table__,
            Attachment.__table__,
            Transaction.__table__,
            SOSRequest.__table__,
            SystemAccess.__table__,
            OrgSettings.__table__,
        ]
        await conn.run_sync(Base.metadata.create_all, tables=tables)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all, tables=tables)


@pytest.mark.asyncio
async def test_user_service_lifecycle():
    async with TestingSessionLocal() as session:
        # 1. Create user
        user, created = await UserService.get_or_create_user(
            session=session,
            telegram_id=111222,
            full_name="Bobur Mirzo",
            language="uz",
        )
        assert created is True
        assert user.telegram_id == 111222
        assert user.lead_status == "new"
        assert user.free_questions_left == settings.FREE_QUESTIONS_LIMIT

        # 2. Get existing user
        same_user, created_again = await UserService.get_or_create_user(
            session=session,
            telegram_id=111222,
        )
        assert created_again is False
        assert same_user.id == user.id

        # 3. Update language
        await UserService.update_language(session, 111222, "ru")
        assert same_user.language == "ru"

        # 4. Update phone (Hard Gate Lead Capture)
        await UserService.update_phone(session, 111222, "+998901234567")
        assert same_user.phone_number == "+998901234567"
        assert same_user.lead_status == "verified_lead"

        # 5. Decrement questions
        assert await UserService.has_questions_available(same_user) is True
        left = await UserService.decrement_question(session, same_user)
        assert left == settings.FREE_QUESTIONS_LIMIT - 1
        assert same_user.free_questions_left == settings.FREE_QUESTIONS_LIMIT - 1

        # 6. Add questions
        updated = await UserService.add_questions(session, same_user.id, 5)
        assert updated is not None
        assert updated.free_questions_left == settings.FREE_QUESTIONS_LIMIT - 1 + 5


@pytest.mark.asyncio
async def test_referral_flow_anti_fraud():
    async with TestingSessionLocal() as session:
        # 1. Create referrer
        referrer, _ = await UserService.get_or_create_user(
            session=session,
            telegram_id=1001,
            full_name="Referrer User",
        )
        ref_link = ReferralService.get_referral_link("yurist_bot", referrer)
        assert "start=ref_1001" in ref_link

        # 2. Friend joins via referral link
        friend, _ = await UserService.get_or_create_user(
            session=session,
            telegram_id=2002,
            full_name="Friend User",
            referred_by_code="ref_1001",
        )
        assert friend.referred_by_id == referrer.id

        # Before phone verification, referrer should NOT get bonus yet
        rewarded = await ReferralService.process_referral_reward(session, friend)
        assert rewarded is None
        assert referrer.free_questions_left == settings.FREE_QUESTIONS_LIMIT

        # Friend verifies phone number -> Anti-fraud reward is triggered
        await UserService.update_phone(session, friend.telegram_id, "+998939998877")
        reward_data = await ReferralService.process_referral_reward(session, friend)
        assert reward_data == (1001, "uz")

        # Check referrer balance increased by 1
        refreshed_referrer = await UserService.get_by_telegram_id(session, 1001)
        assert refreshed_referrer is not None
        assert refreshed_referrer.free_questions_left == settings.FREE_QUESTIONS_LIMIT + 1

        # Check referral stats
        stats = await ReferralService.get_referral_stats(session, referrer)
        assert stats["total_invited"] == 1
        assert stats["verified_count"] == 1
        assert stats["bonus_earned"] == 1

        # 3. Existing user joins with referral code -> Gets attributed to referrer
        existing_user, _ = await UserService.get_or_create_user(
            session=session,
            telegram_id=4005,
            full_name="Existing User",
        )
        assert existing_user.referred_by_id is None
        attributed_user, _ = await UserService.get_or_create_user(
            session=session,
            telegram_id=4005,
            referred_by_code="ref_1001",
        )
        assert attributed_user.referred_by_id == referrer.id

        # 4. Anti-fraud: User tries to use SAME phone number -> Referral bonus withheld
        fraud_user, _ = await UserService.get_or_create_user(
            session=session,
            telegram_id=3004,
            full_name="Fraud Account",
            referred_by_code="ref_1001",
        )
        await UserService.update_phone(session, fraud_user.telegram_id, "+998939998877")
        fraud_reward = await ReferralService.process_referral_reward(session, fraud_user)
        assert fraud_reward is None  # Must withhold bonus because phone already existed!


def test_phone_normalization_utility():
    assert UserService.normalize_phone_number("+998 90 123 45 67") == "+998901234567"
    assert UserService.normalize_phone_number("90 123 45 67") == "+998901234567"
    assert UserService.normalize_phone_number("998901234567") == "+998901234567"
    assert UserService.normalize_phone_number("+998901234567") == "+998901234567"
    assert UserService.normalize_phone_number("+1 (415) 555-2671") == "+14155552671"
    assert UserService.normalize_phone_number("not a phone number") is None
    assert UserService.normalize_phone_number("123") is None


@pytest.mark.asyncio
async def test_anti_self_referral():
    async with TestingSessionLocal() as session:
        # User tries to refer themselves using ref_7777
        user, _ = await UserService.get_or_create_user(
            session=session,
            telegram_id=7777,
            referred_by_code="ref_7777",
        )
        assert user.referred_by_id is None


@pytest.mark.asyncio
async def test_payment_service():
    async with TestingSessionLocal() as session:
        user, _ = await UserService.get_or_create_user(
            session=session,
            telegram_id=3003,
            full_name="Payer User",
        )

        # Create service
        service = Service(
            title_uz="Ekspress Shartnoma Auditi",
            title_ru="Экспресс аудит договора",
            price="150 000 so'm",
            service_type="audit",
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)

        # Create transaction
        tx = await PaymentService.create_transaction(
            session=session,
            user=user,
            amount=Decimal("150000.00"),
            payment_method="p2p_card",
        )
        assert tx.id is not None
        assert tx.payment_status == "pending"

        # Confirm transaction
        confirmed = await PaymentService.confirm_payment(
            session=session,
            transaction_id=tx.id,
            transaction_ref="BANK_PAY_987654",
        )
        assert confirmed is not None
        assert confirmed.payment_status == "completed"
        assert confirmed.transaction_ref == "BANK_PAY_987654"


@pytest.mark.asyncio
async def test_lawyer_unlimited_questions():
    async with TestingSessionLocal() as session:
        # Mock settings.LAWYER_TELEGRAM_ID
        orig_lawyer_id = settings.LAWYER_TELEGRAM_ID
        settings.LAWYER_TELEGRAM_ID = 999888
        try:
            lawyer_user, _ = await UserService.get_or_create_user(
                session=session,
                telegram_id=999888,
                full_name="Advokat Iqboljon",
            )
            assert UserService.is_lawyer(lawyer_user) is True
            assert lawyer_user.is_subscribed is True

            # Question availability should always be True even if free_questions_left is 0
            lawyer_user.free_questions_left = 0
            assert await UserService.has_questions_available(lawyer_user) is True

            # Decrementing should NOT reduce balance
            bal = await UserService.decrement_question(session, lawyer_user)
            assert bal == 0
            assert lawyer_user.free_questions_left == 0
        finally:
            settings.LAWYER_TELEGRAM_ID = orig_lawyer_id


@pytest.mark.asyncio
async def test_access_service_methods():
    """Test AccessService multi-lawyer, groups, and admin retrieval and CRUD."""
    from app.services.access_service import AccessService

    async with TestingSessionLocal() as session:
        # Create multiple lawyers
        lawyer1 = await AccessService.create(
            session=session,
            telegram_id=10001,
            role="lawyer",
            name="Advokat 1",
            description="Toshkent shahri",
            is_active=True,
        )
        assert lawyer1.id is not None

        lawyer2 = await AccessService.create(
            session=session,
            telegram_id=10002,
            role="lawyer",
            name="Advokat 2",
            description="Samarqand viloyati",
            is_active=False,  # Inactive
        )
        group1 = await AccessService.create(
            session=session,
            telegram_id=-100999,
            role="group",
            name="Buyurtmalar guruhi",
            is_active=True,
        )
        assert group1.id is not None

        # Check active lawyers (only lawyer1 should be in active IDs)
        active_lawyer_ids = await AccessService.get_active_lawyer_ids(session)
        assert 10001 in active_lawyer_ids
        assert 10002 not in active_lawyer_ids  # inactive

        # Check is_lawyer helper
        assert await AccessService.is_lawyer(session, 10001) is True
        assert await AccessService.is_lawyer(session, 10002) is False
        assert await AccessService.is_lawyer(session, 99999) is False

        # Check groups
        group_ids = await AccessService.get_active_group_ids(session)
        assert -100999 in group_ids

        # Update lawyer2 to active
        await AccessService.update(session, lawyer2.id, is_active=True)
        active_lawyer_ids = await AccessService.get_active_lawyer_ids(session)
        assert 10002 in active_lawyer_ids
        assert await AccessService.is_lawyer(session, 10002) is True


@pytest.mark.asyncio
async def test_lawyer_table_unlimited_questions_for_existing_user():
    """Test that existing regular users promoted to lawyers in settings table get unlimited messages."""
    from app.services.access_service import AccessService

    async with TestingSessionLocal() as session:
        # 1. Existing regular user with 0 free questions and no subscription
        user, _ = await UserService.get_or_create_user(
            session=session,
            telegram_id=555444,
            full_name="Mijoz Sardor",
        )
        user.free_questions_left = 0
        user.is_subscribed = False
        await session.commit()

        # Regular user should NOT have questions available
        assert await UserService.has_questions_available(user, session=session) is False

        # 2. Add user to Lawyers access table
        await AccessService.create(
            session=session,
            telegram_id=555444,
            role="lawyer",
            name="Advokat Sardor",
            is_active=True,
        )

        # 3. User should now automatically be promoted and have unlimited questions
        await session.refresh(user)
        assert user.lead_status == "lawyer"
        assert user.is_subscribed is True
        assert user.free_questions_left >= 999999
        assert UserService.is_lawyer(user) is True
        assert await UserService.has_questions_available(user, session=session) is True

        # Decrementing should NOT decrease question balance
        bal = await UserService.decrement_question(session, user)
        assert bal >= 999999
        assert user.free_questions_left >= 999999


@pytest.mark.asyncio
async def test_org_settings_and_business_helpers():
    """Test OrgSettingsService and business chat payment helper utilities."""
    from app.bot.handlers.business.messages import extract_phone, is_service_payment_intent

    async with TestingSessionLocal() as session:
        # Default initialization
        settings_rec = await OrgSettingsService.get_settings(session)
        assert settings_rec is not None
        assert settings_rec.card_number == "9860 0001 2345 6789"
        assert settings_rec.card_holder == "Yuridik Xizmatlar"

        # Update
        updated = await OrgSettingsService.update_settings(
            session,
            card_number="8600 9999 8888 7777",
            card_holder="Advokat Iqboljon",
            contact_phone="+998901234567",
        )
        assert updated.card_number == "8600 9999 8888 7777"
        assert updated.card_holder == "Advokat Iqboljon"

        # Re-fetch
        refetched = await OrgSettingsService.get_settings(session)
        assert refetched.card_number == "8600 9999 8888 7777"

    # Helpers
    assert extract_phone("Mening raqamim +998901234567") == "+998901234567"
    assert extract_phone("tel: 99893 111 22 33") == "+998931112233"
    assert extract_phone("telefon raqam yo'q") is None

    assert is_service_payment_intent("xizmat narxi qancha?") is True
    assert is_service_payment_intent("Karta raqam bering") is True
    assert is_service_payment_intent("To'lov qildim, chekni qabul qiling") is True
    assert is_service_payment_intent("Bugun ob-havo qanday?") is False


@pytest.mark.asyncio
async def test_business_chat_services_catalog_and_selection():
    """Test general service inquiry detection, catalog generation, and service selection."""
    from app.bot.handlers.business.messages import (
        detect_service_selection,
        format_services_catalog_text,
        is_general_services_inquiry,
    )
    from app.db.models.service import Service

    # Test inquiries
    assert is_general_services_inquiry("Qanday xizmatlar bor?") is True
    assert is_general_services_inquiry("Assalomu alaykum xizmatlardan foydalanmoqchiman") is True
    assert is_general_services_inquiry("Xizmatlaringiz haqida ma'lumot bering") is True
    assert is_general_services_inquiry("Xizmatlar ro'yxatini tashlang") is True
    assert is_general_services_inquiry("Xizmatlar narxlari qanday?") is True
    assert is_general_services_inquiry("Biznesimda soliq tekshiruvi boshlandi") is False

    # Create dummy service sequence
    s1 = Service(
        id=1,
        title_uz="Shaxsiy konsultatsiya",
        title_ru="Консультация",
        description_uz="24 soat ichida to'liq tahlil",
        price="150 000 so'm",
        service_type="consultation",
        is_active=True,
    )
    s2 = Service(
        id=2,
        title_uz="Shartnoma auditi",
        title_ru="Аудит договора",
        description_uz="Xatarlarni tekshirish",
        price="300 000 so'm",
        service_type="audit",
        is_active=True,
    )
    s3 = Service(
        id=3,
        title_uz="Da'vo arizasi tuzish",
        title_ru="Исковое заявление",
        description_uz="Sud arizasi",
        price="500 000 so'm",
        service_type="claim",
        is_active=True,
    )
    services = [s1, s2, s3]

    # Test catalog text formatting
    catalog_uz = format_services_catalog_text(services, lang="uz")
    assert "Bizning professional yuridik xizmatlarimiz" in catalog_uz
    assert "1. Shaxsiy konsultatsiya" in catalog_uz
    assert "150 000 so'm" in catalog_uz
    assert "2. Shartnoma auditi" in catalog_uz
    assert "300 000 so'm" in catalog_uz
    assert "3. Da'vo arizasi tuzish" in catalog_uz
    assert "500 000 so'm" in catalog_uz

    # Test selection by number (with is_awaiting=True)
    assert detect_service_selection("1", services, is_awaiting=True) == s1
    assert detect_service_selection("2", services, is_awaiting=True) == s2
    assert detect_service_selection("3-xizmat", services, is_awaiting=True) == s3
    assert detect_service_selection("ikkinchisi", services, is_awaiting=True) == s2

    # Test selection by keyword (requires is_awaiting=True per requirement to see catalog first)
    assert detect_service_selection("Menga shartnoma tekshirish kerak", services, is_awaiting=True) == s2
    assert detect_service_selection("Sudga da'vo arizasi bermoqchiman", services, is_awaiting=True) == s3
    assert detect_service_selection("Menga shartnoma tekshirish kerak", services, is_awaiting=False) is None
    assert detect_service_selection("Oddiy salom", services, is_awaiting=True) is None


def test_string_price_formatting_and_extraction():
    assert PaymentService.extract_numeric_amount("40 000 dan boshlanadi") == Decimal("40000.00")
    assert PaymentService.extract_numeric_amount("150000") == Decimal("150000.00")
    assert PaymentService.extract_numeric_amount("Kelishuv asosida") == Decimal("0.00")
    assert PaymentService.extract_numeric_amount(Decimal("250000.50")) == Decimal("250000.50")

    assert PaymentService.format_service_price("40 000 dan boshlanadi") == "40 000 dan boshlanadi"
    assert PaymentService.format_service_price("150000") == "150 000 so'm"
    assert PaymentService.format_service_price("150 000 so'm") == "150 000 so'm"
    assert PaymentService.format_service_price(Decimal(50000)) == "50 000 so'm"


def test_office_address_inquiry_and_formatting():
    from app.db.models.org_settings import OrgSettings
    from app.services.org_settings_service import OrgSettingsService

    # Test address detection
    assert OrgSettingsService.is_office_address_inquiry("Ofisingiz qayerda?") is True
    assert OrgSettingsService.is_office_address_inquiry("Manzilingizni bering") is True
    assert OrgSettingsService.is_office_address_inquiry("Lokatsiyani yuboring") is True
    assert OrgSettingsService.is_office_address_inquiry("Где находится ваш офис?") is True
    assert OrgSettingsService.is_office_address_inquiry("Адрес офиса") is True
    assert OrgSettingsService.is_office_address_inquiry("Aliment bo'yicha ariza yozmoqchiman") is False

    # Test format text
    settings_obj = OrgSettings(
        office_address="Toshkent sh., Amir Temur shoh ko'chasi, 42-uy",
        contact_phone="+998901234567",
        working_hours="Dushanba - Shanba, 09:00 - 18:00",
    )
    uz_text = OrgSettingsService.format_office_address_text(settings_obj, lang="uz")
    assert "Toshkent sh., Amir Temur shoh ko'chasi, 42-uy" in uz_text
    assert "+998901234567" in uz_text
    assert "09:00 - 18:00" in uz_text

    ru_text = OrgSettingsService.format_office_address_text(settings_obj, lang="ru")
    assert "Toshkent sh., Amir Temur shoh ko'chasi, 42-uy" in ru_text
    assert "+998901234567" in ru_text


def test_consultation_intent_triggers_catalog():
    from app.bot.handlers.business.messages import is_general_services_inquiry

    assert is_general_services_inquiry("konsultatsiya olaman") is True
    assert is_general_services_inquiry("konsultatsiya olmoqchiman") is True
    assert is_general_services_inquiry("xizmatdan foydalanaman") is True
    assert is_general_services_inquiry("xizmatlardan foydalanmoqchiman") is True
    assert is_general_services_inquiry("konsultatsiya") is True


def test_office_service_address_privacy_and_confirmation():
    from app.db.models.org_settings import OrgSettings
    from app.services.org_settings_service import OrgSettingsService

    # 1. Test is_office_service_ref
    office_title = "Malakali yurist va advokatdan ofisda korishib konsultatsiya olish"
    assert OrgSettingsService.is_office_service_ref(office_title) is True
    assert OrgSettingsService.is_office_service_ref("Ofisda yurist konsultatsiyasi") is True
    assert OrgSettingsService.is_office_service_ref("Telegram orqali konsultatsiya") is False
    assert OrgSettingsService.is_office_service_ref("Shartnoma auditi") is False

    # 2. Test format_office_service_notice (address withheld before payment)
    notice_uz = OrgSettingsService.format_office_service_notice("uz")
    assert "to'lov" in notice_uz.lower()
    assert "Malakali yurist va advokatdan ofisda ko'rishib konsultatsiya olish" in notice_uz

    notice_ru = OrgSettingsService.format_office_service_notice("ru")
    assert "оплата" in notice_ru.lower() or "оплату" in notice_ru.lower()

    # 3. Test format_payment_confirmed_text (address revealed ONLY after payment confirmed for office service)
    settings_obj = OrgSettings(
        office_address="Toshkent sh., Chilonzor tumani, S mavze 1A/2",
        contact_phone="+998 (94) 304 27 72",
        working_hours="09:00 - 19:00",
    )

    # Office service -> MUST contain office address
    conf_office = OrgSettingsService.format_payment_confirmed_text(office_title, settings_obj, "uz")
    assert "Toshkent sh., Chilonzor tumani, S mavze 1A/2" in conf_office
    assert "+998 (94) 304 27 72" in conf_office

    # Non-office service -> MUST NOT reveal office address
    conf_online = OrgSettingsService.format_payment_confirmed_text("Online konsultatsiya", settings_obj, "uz")
    assert "Toshkent sh., Chilonzor tumani, S mavze 1A/2" not in conf_online


@pytest.mark.asyncio
async def test_has_confirmed_office_consultation_db():
    async with TestingSessionLocal() as session:
        user, _ = await UserService.get_or_create_user(session, telegram_id=999888, full_name="Vali")

        # Before any payment
        assert await PaymentService.has_confirmed_office_consultation(session, user.id) is False

        # Create pending office transaction
        tx = await PaymentService.create_transaction(
            session=session,
            user=user,
            amount="100000",
            payment_method="p2p_card",
            transaction_ref="Malakali yurist va advokatdan ofisda korishib konsultatsiya olish",
        )
        assert await PaymentService.has_confirmed_office_consultation(session, user.id) is False

        # Confirm payment
        await PaymentService.confirm_payment(session, tx.id)
        assert await PaymentService.has_confirmed_office_consultation(session, user.id) is True


@pytest.mark.asyncio
async def test_native_location_extraction_and_sending():
    from unittest.mock import AsyncMock

    from app.db.models.org_settings import OrgSettings
    from app.services.org_settings_service import OrgSettingsService

    yandex_address = (
        "Toshkent shahar, Chilonzor tumani, S mavze 1A/2\n"
        "https://yandex.com/maps?whatshere%5Bpoint%5D=69.20197%2C41.278871&whatshere%5Bzoom%5D=18.958878&"
        "ll=69.20197000000003%2C41.27887099922946&z=18.958878&si=xrvj9bmbxz387zdhwcw15k2htw"
    )

    # 1. Test clean address strips URL
    clean = OrgSettingsService.get_clean_office_address(yandex_address)
    assert clean == "Toshkent shahar, Chilonzor tumani, S mavze 1A/2"

    # 2. Test coordinate extraction
    coords = OrgSettingsService.extract_office_coordinates(yandex_address)
    assert coords is not None
    lat, lon = coords
    assert round(lat, 4) == 41.2789
    assert round(lon, 4) == 69.2020

    # 3. Test sending native location
    bot_mock = AsyncMock()
    bot_mock.send_location = AsyncMock()

    settings_obj = OrgSettings(office_address=yandex_address)
    sent = await OrgSettingsService.send_office_location(
        bot=bot_mock,
        chat_id=123456,
        settings_record=settings_obj,
        business_connection_id="bc_999",
    )
    assert sent is True
    assert bot_mock.send_location.called
    kwargs = bot_mock.send_location.call_args[1]
    assert kwargs["chat_id"] == 123456
    assert round(kwargs["latitude"], 4) == 41.2789
    assert round(kwargs["longitude"], 4) == 69.2020
    assert kwargs["business_connection_id"] == "bc_999"
