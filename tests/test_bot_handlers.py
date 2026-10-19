"""Tests for Telegram Bot handlers, keyboards, and dispatcher configuration."""


import pytest
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.keyboards.keyboards import (
    cta_keyboard,
    language_selection_kb,
    main_menu_kb,
    payment_methods_kb,
    phone_request_kb,
    referral_share_kb,
    services_catalog_kb,
    settings_kb,
    sos_options_kb,
)
from app.bot.main import setup_bot_dispatcher
from app.db.models.service import Service


def test_dispatcher_router_registration():
    dp = Dispatcher(storage=MemoryStorage())
    setup_bot_dispatcher(dp)

    # Sub-routers included: start, registration, services, referral, sos, helplines, audit, inquiry, business
    assert len(dp.sub_routers) == 9


def test_keyboards_structure():
    # 1. Language keyboard
    lang_kb = language_selection_kb()
    assert len(lang_kb.inline_keyboard[0]) == 2
    assert lang_kb.inline_keyboard[0][0].callback_data == "set_lang:uz"
    assert lang_kb.inline_keyboard[0][1].callback_data == "set_lang:ru"

    # 2. Phone request keyboard
    phone_kb = phone_request_kb("uz")
    assert phone_kb.keyboard[0][0].request_contact is True

    # 3. Main menu keyboard
    menu_uz = main_menu_kb("uz")
    assert len(menu_uz.keyboard) == 4
    assert menu_uz.keyboard[0][0].text == "💬 Yuridik savol berish"

    menu_ru = main_menu_kb("ru")
    assert menu_ru.keyboard[0][0].text == "💬 Задать правовой вопрос"

    # 4. CTA keyboard
    cta_kb = cta_keyboard("audit", "uz")
    assert any("audit" in btn.callback_data for row in cta_kb.inline_keyboard for btn in row)
    assert any(
        "show_referral" in btn.callback_data for row in cta_kb.inline_keyboard for btn in row
    )

    # 4b. Referral share keyboard
    ref_kb = referral_share_kb("https://t.me/yurist_bot?start=ref_123", "uz")
    assert any("https://t.me/share/url" in (btn.url or "") for row in ref_kb.inline_keyboard for btn in row)
    assert any("refresh_referral" in (btn.callback_data or "") for row in ref_kb.inline_keyboard for btn in row)

    # 5. SOS options keyboard
    sos_kb = sos_options_kb("uz")
    assert len(sos_kb.inline_keyboard) == 3
    assert sos_kb.inline_keyboard[0][0].callback_data == "sos_guide:police"

    # 6. Services catalog keyboard
    mock_services = [
        Service(
            id=1,
            title_uz="Konsultatsiya",
            title_ru="Консультация",
            price="100 000 so'm",
            service_type="consultation",
        ),
        Service(
            id=2,
            title_uz="Sudda vakillik",
            title_ru="Суд",
            price="2 000 000 so'm",
            service_type="court",
        ),
    ]
    catalog_kb = services_catalog_kb(mock_services, "uz")
    assert len(catalog_kb.inline_keyboard) == 3
    assert catalog_kb.inline_keyboard[0][0].callback_data == "buy_service:1"
    assert catalog_kb.inline_keyboard[2][0].callback_data == "contact_lawyer"

    # 7. Payment methods keyboard
    pay_kb = payment_methods_kb(1, "uz")
    assert len(pay_kb.inline_keyboard) == 4
    assert pay_kb.inline_keyboard[0][0].callback_data == "pay_p2p:1"
    assert pay_kb.inline_keyboard[1][0].callback_data == "pay_stars:1"
    assert pay_kb.inline_keyboard[3][0].callback_data == "back_to_services"

    # 8. Settings keyboard
    set_kb = settings_kb("uz")
    assert len(set_kb.inline_keyboard) == 2
    assert set_kb.inline_keyboard[0][0].callback_data == "settings:change_lang"


@pytest.mark.asyncio
async def test_contact_submission_success():
    from unittest.mock import AsyncMock, MagicMock

    from app.bot.handlers.public.registration import handle_contact_submission

    message = MagicMock()
    message.from_user.id = 555666
    message.contact.user_id = 555666
    message.contact.phone_number = "901234567"
    message.answer = AsyncMock()

    session = AsyncMock()
    bot = MagicMock()

    mock_user = MagicMock()
    mock_user.language = "uz"
    mock_user.phone_number = "+998901234567"
    mock_user.free_questions_left = 3

    from app.services.referral_service import ReferralService
    from app.services.user_service import UserService

    orig_update_phone = UserService.update_phone
    orig_reward = ReferralService.process_referral_reward
    UserService.update_phone = AsyncMock(return_value=mock_user)
    ReferralService.process_referral_reward = AsyncMock(return_value=None)

    try:
        await handle_contact_submission(message, session, bot, user=mock_user)
        assert message.answer.called
        call_text = message.answer.call_args[0][0]
        assert "Telefon raqamingiz muvaffaqiyatli tasdiqlandi" in call_text
        assert "+998901234567" in call_text
    finally:
        UserService.update_phone = orig_update_phone
        ReferralService.process_referral_reward = orig_reward


@pytest.mark.asyncio
async def test_contact_spoofing_prevented():
    from unittest.mock import AsyncMock, MagicMock

    from app.bot.handlers.public.registration import handle_contact_submission

    message = MagicMock()
    message.from_user.id = 555666
    message.contact.user_id = 999999  # Different person's contact!
    message.contact.phone_number = "+998909999999"
    message.answer = AsyncMock()

    session = AsyncMock()
    bot = MagicMock()
    mock_user = MagicMock()
    mock_user.language = "uz"

    await handle_contact_submission(message, session, bot, user=mock_user)
    assert message.answer.called
    call_text = message.answer.call_args[0][0]
    assert "o'zingizning shaxsiy telefon raqamingizni yuboring" in call_text


@pytest.mark.asyncio
async def test_text_phone_submission_success():
    from unittest.mock import AsyncMock, MagicMock

    from app.bot.handlers.public.registration import handle_text_phone_submission
    from app.services.referral_service import ReferralService
    from app.services.user_service import UserService

    message = MagicMock()
    message.from_user.id = 777888
    message.text = "+998 90 777 88 99"
    message.answer = AsyncMock()

    session = AsyncMock()
    bot = MagicMock()

    unverified_user = MagicMock()
    unverified_user.phone_number = None
    unverified_user.language = "uz"

    verified_user = MagicMock()
    verified_user.language = "uz"
    verified_user.phone_number = "+998907778899"
    verified_user.free_questions_left = 3

    orig_update_phone = UserService.update_phone
    orig_reward = ReferralService.process_referral_reward
    UserService.update_phone = AsyncMock(return_value=verified_user)
    ReferralService.process_referral_reward = AsyncMock(return_value=None)

    try:
        await handle_text_phone_submission(message, session, bot, user=unverified_user)
        assert message.answer.called
        call_text = message.answer.call_args[0][0]
        assert "Telefon raqamingiz muvaffaqiyatli tasdiqlandi" in call_text
        assert "+998907778899" in call_text
    finally:
        UserService.update_phone = orig_update_phone
        ReferralService.process_referral_reward = orig_reward


@pytest.mark.asyncio
async def test_user_context_middleware_resolves_update():
    from unittest.mock import AsyncMock, MagicMock

    from aiogram.types import Chat, Message, Update
    from aiogram.types import User as TgUser

    from app.bot.middlewares.user_middleware import UserContextMiddleware
    from app.services.user_service import UserService

    middleware = UserContextMiddleware()
    update = Update(
        update_id=100,
        message=Message(
            message_id=1,
            date=123,
            chat=Chat(id=111, type="private"),
            from_user=TgUser(id=111, is_bot=False, first_name="Ali"),
            text="Savol",
        ),
    )

    mock_db_user = MagicMock()
    mock_db_user.id = 1
    mock_db_user.telegram_id = 111
    mock_db_user.phone_number = "+998901112233"

    orig_get_or_create = UserService.get_or_create_user
    UserService.get_or_create_user = AsyncMock(return_value=(mock_db_user, False))

    async def dummy_handler(evt, data):
        return data.get("user")

    data = {"session": AsyncMock()}
    try:
        res = await middleware(dummy_handler, update, data)
        assert res is not None
        assert res.telegram_id == 111
        assert res.phone_number == "+998901112233"
    finally:
        UserService.get_or_create_user = orig_get_or_create


@pytest.mark.asyncio
async def test_handle_inquiry_button_click_verified_user():
    from unittest.mock import AsyncMock, MagicMock

    from app.bot.handlers.public.inquiry import handle_inquiry_button_click

    message = MagicMock()
    message.from_user.id = 111
    message.answer = AsyncMock()

    verified_user = MagicMock()
    verified_user.language = "uz"
    verified_user.phone_number = "+998901234567"
    verified_user.free_questions_left = 3
    verified_user.is_subscribed = False

    await handle_inquiry_button_click(message, user=verified_user)
    assert message.answer.called
    response = message.answer.call_args[0][0]
    assert "Yuridik savol berish" in response
    assert "Savolingizni matn yoki ovozli xabar" in response


@pytest.mark.asyncio
async def test_handle_inquiry_button_click_unverified_user():
    from unittest.mock import AsyncMock, MagicMock

    from app.bot.handlers.public.inquiry import handle_inquiry_button_click

    message = MagicMock()
    message.from_user.id = 111
    message.chat.type = "private"
    message.answer = AsyncMock()

    unverified_user = MagicMock()
    unverified_user.language = "uz"
    unverified_user.phone_number = None

    await handle_inquiry_button_click(message, user=unverified_user)
    assert message.answer.called
    response = message.answer.call_args[0][0]
    assert "telefon raqamingizni yuboring" in response


@pytest.mark.asyncio
async def test_handle_referral_menu_and_callback():
    from unittest.mock import AsyncMock, MagicMock

    from app.bot.handlers.public.referral import handle_referral_callback, handle_referral_menu

    # 1. Test handle_referral_menu
    message = MagicMock()
    message.from_user.id = 12345
    message.answer = AsyncMock()

    bot = MagicMock()
    bot.get_me = AsyncMock()
    bot.get_me.return_value.username = "test_yurist_bot"

    user = MagicMock()
    user.id = 1
    user.telegram_id = 12345
    user.referral_code = "ref_12345"
    user.language = "uz"
    user.free_questions_left = 3

    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 0
    session.execute.return_value = mock_result

    await handle_referral_menu(message, session, bot, user)
    assert message.answer.called
    text = message.answer.call_args[0][0]
    kb = message.answer.call_args[1]["reply_markup"]
    assert "Do'stlarni Taklif Qilish Dasturi" in text
    assert "ref_12345" in text
    assert "https://t.me/share/url" in kb.inline_keyboard[0][0].url

    from aiogram.types import Message

    # 2. Test handle_referral_callback (show_referral)
    callback = MagicMock()
    callback.data = "show_referral"
    callback.from_user.id = 12345
    callback.answer = AsyncMock()
    callback.message = MagicMock(spec=Message)
    callback.message.answer = AsyncMock()

    await handle_referral_callback(callback, session, bot, user)
    assert callback.answer.called
    assert callback.message.answer.called
    cb_text = callback.message.answer.call_args[0][0]
    assert "Do'stlarni Taklif Qilish Dasturi" in cb_text

    # 3. Test handle_referral_callback (refresh_referral)
    refresh_cb = MagicMock()
    refresh_cb.data = "refresh_referral"
    refresh_cb.from_user.id = 12345
    refresh_cb.answer = AsyncMock()
    refresh_cb.message = MagicMock(spec=Message)
    refresh_cb.message.edit_text = AsyncMock()

    await handle_referral_callback(refresh_cb, session, bot, user)
    assert refresh_cb.answer.called
    assert refresh_cb.message.edit_text.called


@pytest.mark.asyncio
async def test_services_and_pricing_handlers():
    from unittest.mock import AsyncMock, MagicMock

    from aiogram.types import Message

    from app.bot.handlers.public.services import (
        handle_back_to_services,
        handle_buy_service,
        handle_order_service_cta,
        handle_p2p_payment,
        handle_services_menu,
    )
    from app.db.models.service import Service

    message = MagicMock()
    message.answer = AsyncMock()

    mock_service = Service(
        id=10,
        title_uz="Test Konsultatsiya",
        title_ru="Тест Консультация",
        description_uz="Batafsil tahlil va maslahat",
        description_ru="Подробный анализ",
        price="150 000 so'm",
        service_type="consultation",
        is_active=True,
    )

    session = AsyncMock()
    user = MagicMock()
    user.language = "uz"
    user.id = 1
    user.full_name = "Sinovchi Mijoz"
    user.phone_number = "+998901234567"

    # 1. Services menu
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [mock_service]
    session.execute.return_value = mock_res

    await handle_services_menu(message, session, user)
    assert message.answer.called
    menu_text = message.answer.call_args[0][0]
    assert "Yuridik Xizmatlar" in menu_text

    # 2. Buy service details
    cb = MagicMock()
    cb.data = "buy_service:10"
    cb.message = MagicMock(spec=Message)
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()

    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = mock_service
    session.execute.return_value = mock_scalar

    await handle_buy_service(cb, session, user)
    assert cb.message.edit_text.called
    details_text = cb.message.edit_text.call_args[0][0]
    assert "Test Konsultatsiya" in details_text
    assert "150 000 so'm" in details_text

    # 3. Back to services
    back_cb = MagicMock()
    back_cb.data = "back_to_services"
    back_cb.message = MagicMock(spec=Message)
    back_cb.message.edit_text = AsyncMock()
    back_cb.answer = AsyncMock()

    session.execute.return_value = mock_res
    await handle_back_to_services(back_cb, session, user)
    assert back_cb.message.edit_text.called

    # 4. Order service CTA
    cta_cb = MagicMock()
    cta_cb.data = "order_service:consultation"
    cta_cb.message = MagicMock(spec=Message)
    cta_cb.message.answer = AsyncMock()
    cta_cb.answer = AsyncMock()

    session.execute.return_value = mock_scalar
    await handle_order_service_cta(cta_cb, session, user)
    assert cta_cb.message.answer.called

    # 5. P2P Payment
    p2p_cb = MagicMock()
    p2p_cb.data = "pay_p2p:10"
    p2p_cb.message = MagicMock(spec=Message)
    p2p_cb.message.answer = AsyncMock()
    p2p_cb.answer = AsyncMock()

    bot = MagicMock()
    bot.send_message = AsyncMock()

    await handle_p2p_payment(p2p_cb, session, bot, user)
    assert p2p_cb.message.answer.called
    p2p_text = p2p_cb.message.answer.call_args[0][0]
    assert "Karta orqali to'lov" in p2p_text


@pytest.mark.asyncio
async def test_helplines_reply_button_handlers():
    from unittest.mock import AsyncMock, MagicMock

    from aiogram.types import Message

    from app.bot.handlers.public.helplines import (
        handle_helpline_back_to_main,
        handle_helpline_category_click,
        handle_helplines_menu,
    )
    from app.db.models.helpline import Helpline
    from app.services.helpline_service import HelplineService

    session = AsyncMock()
    user = MagicMock()
    user.language = "uz"

    # Mock helpline
    h1 = Helpline(
        id=1,
        category_uz="Sud tizimi",
        category_ru="Судебная система",
        organization_uz="Oliy sud",
        organization_ru="Верховный суд",
        phone_number="1144",
        description_uz="Ishonch telefoni",
        order=1,
        is_active=True,
    )

    orig_categories = HelplineService.get_active_categories
    orig_by_cat = HelplineService.get_by_category
    orig_seed = HelplineService.seed_default_helplines

    HelplineService.get_active_categories = AsyncMock(return_value=[("Sud tizimi", "Судебная система")])
    HelplineService.get_by_category = AsyncMock(return_value=[h1])
    HelplineService.seed_default_helplines = AsyncMock()

    try:
        # 1. Main helplines menu message
        msg1 = MagicMock(spec=Message)
        msg1.answer = AsyncMock()
        await handle_helplines_menu(msg1, session, user)
        assert msg1.answer.called
        text1 = msg1.answer.call_args[0][0]
        assert "Ishonch telefonlari katalogi" in text1
        kb1 = msg1.answer.call_args[1]["reply_markup"]
        assert any("📂 Sud tizimi" in btn.text for row in kb1.keyboard for btn in row)
        assert any("🔙 Asosiy menyuga qaytish" in btn.text for row in kb1.keyboard for btn in row)

        # 2. Click category reply button
        msg2 = MagicMock(spec=Message)
        msg2.text = "📂 Sud tizimi"
        msg2.answer = AsyncMock()
        await handle_helpline_category_click(msg2, session, user)
        assert msg2.answer.called
        text2 = msg2.answer.call_args[0][0]
        assert "Oliy sud" in text2
        assert "1144" in text2

        # 3. Back to main menu
        msg3 = MagicMock(spec=Message)
        msg3.text = "🔙 Asosiy menyuga qaytish"
        msg3.answer = AsyncMock()
        await handle_helpline_back_to_main(msg3, user)
        assert msg3.answer.called
        text3 = msg3.answer.call_args[0][0]
        assert "Asosiy menyu:" in text3
    finally:
        HelplineService.get_active_categories = orig_categories
        HelplineService.get_by_category = orig_by_cat
        HelplineService.seed_default_helplines = orig_seed


@pytest.mark.asyncio
async def test_dynamic_cta_and_service_fulfillment():
    from unittest.mock import AsyncMock, MagicMock

    from aiogram.types import Message

    from app.bot.handlers.public.services import (
        handle_payment_approval,
        handle_rate_service,
        handle_service_completed,
    )
    from app.bot.keyboards.keyboards import cta_keyboard, service_fulfillment_kb
    from app.db.models.transaction import Transaction
    from app.services.ai.llm_client import detect_service_cta_from_question

    # 1. Test heuristic detector
    assert detect_service_cta_from_question("Qarzimni undirish uchun sudga ariza yozish kerak") == "claim"
    assert detect_service_cta_from_question("Ijara shartnomasini tekshirib berolasizmi?") == "audit"
    assert detect_service_cta_from_question("Ertaga sud majlisi bo'ladi, himoyachi kerak") == "court"
    assert detect_service_cta_from_question("MChJ ochish va korxona soliqlari haqida") == "business"
    assert detect_service_cta_from_question("Oddiy savolim bor edi") == "consultation"

    # 2. Test dynamic CTA keyboards
    kb_claim = cta_keyboard("claim", "uz")
    assert kb_claim is not None
    assert "Da'vo arizasi" in kb_claim.inline_keyboard[0][0].text
    assert kb_claim.inline_keyboard[0][0].callback_data == "order_service:claim"

    kb_audit = cta_keyboard("audit", "uz")
    assert kb_audit is not None
    assert "Shartnoma" in kb_audit.inline_keyboard[0][0].text
    assert kb_audit.inline_keyboard[0][0].callback_data == "order_service:audit"

    # 3. Test service fulfillment keyboard
    f_kb = service_fulfillment_kb(tx_id=99, ref_link="https://t.me/bot?start=ref_1", lang="uz")
    assert len(f_kb.inline_keyboard[0]) == 5
    assert f_kb.inline_keyboard[0][4].callback_data == "rate_srv:tx_99_5"
    assert "Yaqinlarga ulashish" in f_kb.inline_keyboard[1][0].text

    # 4. Test payment approval sets pay_done button
    session = AsyncMock()
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.get_me = AsyncMock()
    bot.get_me.return_value.username = "test_bot"

    from app.db.models.user import User

    client_user = User(
        id=1,
        telegram_id=987654,
        full_name="Sinovchi",
        language="uz",
    )

    tx = Transaction(
        id=77,
        user_id=1,
        amount=150000,
        payment_method="p2p_card",
        payment_status="pending",
    )
    mock_tx_res = MagicMock()
    mock_tx_res.scalar_one_or_none.side_effect = [client_user, tx, client_user, tx, client_user]
    session.execute.return_value = mock_tx_res

    approval_cb = MagicMock()
    approval_cb.data = "pay_ok:tx_77"
    approval_cb.from_user.full_name = "Admin Alisher"
    approval_cb.answer = AsyncMock()
    approval_cb.message = MagicMock(spec=Message)
    approval_cb.message.caption = "To'lov cheki"
    approval_cb.message.edit_caption = AsyncMock()

    from app.services.payment_service import PaymentService
    orig_confirm = PaymentService.confirm_payment
    PaymentService.confirm_payment = AsyncMock(return_value=tx)

    try:
        await handle_payment_approval(approval_cb, session, bot)
        assert approval_cb.message.edit_caption.called
        caption_updated = approval_cb.message.edit_caption.call_args[1]["caption"]
        assert "TO'LOV TASDIQLANDI" in caption_updated
        markup_updated = approval_cb.message.edit_caption.call_args[1]["reply_markup"]
        assert "pay_done:tx_77" in markup_updated.inline_keyboard[0][0].callback_data

        # 5. Test pay_done marks fulfilled and notifies user
        done_cb = MagicMock()
        done_cb.data = "pay_done:tx_77"
        done_cb.from_user.full_name = "Lawyer Jasur"
        done_cb.answer = AsyncMock()
        done_cb.message = MagicMock(spec=Message)
        done_cb.message.caption = "Old caption"
        done_cb.message.edit_caption = AsyncMock()

        await handle_service_completed(done_cb, session, bot)
        assert done_cb.message.edit_caption.called
        assert tx.payment_status == "fulfilled"
        assert bot.send_message.called

        # 6. Test rate_srv callback
        rate_cb = MagicMock()
        rate_cb.data = "rate_srv:tx_77_5"
        rate_cb.from_user.id = 123
        rate_cb.answer = AsyncMock()
        rate_cb.message = MagicMock(spec=Message)
        rate_cb.message.edit_text = AsyncMock()

        user_mock = MagicMock()
        user_mock.language = "uz"
        user_mock.referral_code = "ref_123"

        await handle_rate_service(rate_cb, session, bot, user_mock)
        assert rate_cb.message.edit_text.called
        edit_text = rate_cb.message.edit_text.call_args[0][0]
        assert "Katta rahmat" in edit_text
    finally:
        PaymentService.confirm_payment = orig_confirm


@pytest.mark.asyncio
async def test_services_details_has_no_guarantee():
    from app.bot.handlers.public.services import format_service_details_text

    text_uz = format_service_details_text("Yuridik audit", "Shartnoma tekshirish", "100 000 so'm", "uz")
    assert "Kafolat" not in text_uz
    assert "🛡" not in text_uz

    text_ru = format_service_details_text("Юридический аудит", "Проверка договора", "100 000 сум", "ru")
    assert "Гарантия" not in text_ru
    assert "🛡" not in text_ru


@pytest.mark.asyncio
async def test_gratitude_inquiry_response():
    from unittest.mock import AsyncMock, MagicMock, patch

    from aiogram.types import Chat, Message
    from aiogram.types import User as TgUser

    from app.bot.handlers.public.inquiry import process_aggregated_inquiry
    from app.services.chat_service import ChatService
    from app.services.inquiry_debouncer import BufferedMessage

    user_mock = MagicMock()
    user_mock.id = 55
    user_mock.telegram_id = 12345
    user_mock.language = "uz"
    user_mock.phone_number = "+998901234567"
    user_mock.question_count = 1

    msg = MagicMock(spec=Message)
    msg.message_id = 99
    msg.text = "Rahmat, sog' bo'ling!"
    msg.caption = None
    msg.chat = Chat(id=12345, type="private")
    msg.from_user = TgUser(id=12345, is_bot=False, first_name="Dilshod")
    msg.answer = AsyncMock()

    bot = AsyncMock()

    batch = [
        BufferedMessage(
            logged_msg_id=1,
            message=msg,
            text="Rahmat, sog' bo'ling!",
            received_at=12345.0,
        )
    ]

    mock_session = AsyncMock()
    scalar_mock = MagicMock()
    scalar_mock.scalar_one_or_none.return_value = user_mock
    mock_session.execute.return_value = scalar_mock

    with patch("app.bot.handlers.public.inquiry.AsyncSessionLocal") as mock_session_local, \
         patch.object(ChatService, "log_message", new_callable=AsyncMock):
        mock_session_local.return_value.__aenter__.return_value = mock_session
        await process_aggregated_inquiry(user=user_mock, batch=batch, bot=bot)

    assert msg.answer.called
    reply_text = msg.answer.call_args[0][0]
    assert "Salomat bo’ling!" in reply_text
    assert "Ishlaringizga omad tilayman!" in reply_text




