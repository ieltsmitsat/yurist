"""Tests for inquiry debouncing/aggregation and conversation history memory."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import settings
from app.db.models.chat_message import ChatMessage
from app.db.models.user import User
from app.services.ai.llm_client import LegalAnalysisResult, LLMService
from app.services.chat_service import ChatService
from app.services.inquiry_debouncer import BufferedMessage, InquiryDebouncer, inquiry_debouncer
from app.services.inquiry_service import InquiryService
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_inquiry_debouncer_aggregates_multiple_messages():
    """Verify that multiple consecutive messages are aggregated into a single inquiry."""
    processed_batches: list[list[BufferedMessage]] = []

    async def mock_processor(user: User, batch: list[BufferedMessage], bot: MagicMock) -> None:
        processed_batches.append(batch)

    # Use a small debounce interval (0.05s) for fast testing
    debouncer = InquiryDebouncer(processor=mock_processor, debounce_seconds=0.05)

    user = MagicMock(spec=User)
    user.id = 42
    bot = MagicMock()

    msg1 = MagicMock()
    msg1.text = "Salom yaxshimisiz"
    msg2 = MagicMock()
    msg2.text = "Menda meros bo'yicha savol bor edi"

    # Add message 1
    await debouncer.add_message(user=user, message=msg1, logged_msg_id=1, bot=bot)
    assert 42 in debouncer._queues
    assert len(debouncer._queues[42].messages) == 1

    # Add message 2 before debounce expires (should reset timer and aggregate)
    await asyncio.sleep(0.01)
    await debouncer.add_message(user=user, message=msg2, logged_msg_id=2, bot=bot)
    assert len(debouncer._queues[42].messages) == 2

    # Wait for debounce window to elapse
    await asyncio.sleep(0.08)

    # Processor should have been called exactly once with both messages
    assert len(processed_batches) == 1
    batch = processed_batches[0]
    assert len(batch) == 2
    assert batch[0].text == "Salom yaxshimisiz"
    assert batch[1].text == "Menda meros bo'yicha savol bor edi"
    assert debouncer._queues.get(42) is None


@pytest.mark.asyncio
async def test_inquiry_debouncer_flush_immediately():
    """Verify flush_user executes pending messages immediately without waiting for timer."""
    called = []

    async def mock_processor(user: User, batch: list[BufferedMessage], bot: MagicMock) -> None:
        called.append(batch)

    debouncer = InquiryDebouncer(processor=mock_processor, debounce_seconds=5.0)

    user = MagicMock(spec=User)
    user.id = 99
    bot = MagicMock()

    msg = MagicMock()
    msg.text = "Yuridik savol"

    await debouncer.add_message(user=user, message=msg, logged_msg_id=10, bot=bot)
    assert len(called) == 0

    # Flush immediately
    await debouncer.flush_user(99)
    assert len(called) == 1
    assert called[0][0].text == "Yuridik savol"


@pytest.mark.asyncio
async def test_chat_service_recent_history_context_formatting():
    """Verify ChatService formats past messages chronologically with role labels and timestamps."""
    session = AsyncMock()

    yesterday = datetime.now(UTC) - timedelta(days=1)
    msg1 = ChatMessage(
        user_id=1,
        telegram_id=111,
        sender_type="user",
        text="Meni ishdan noqonuniy bo'shatishmoqchi",
    )
    msg1.created_at = yesterday

    msg2 = ChatMessage(
        user_id=1,
        telegram_id=111,
        sender_type="bot",
        text="Mehnat kodeksining 161-moddasiga ko'ra ogohlantirish berilishi shart.",
    )
    msg2.created_at = yesterday + timedelta(minutes=1)

    mock_scalars = MagicMock()
    # Mock returns descending order from DB
    mock_scalars.all.return_value = [msg2, msg1]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    session.execute.return_value = mock_result

    history = await ChatService.get_recent_history_context(
        session=session,
        user_id=1,
        limit=5,
        language="uz",
    )

    assert history is not None
    lines = history.split("\n")
    assert len(lines) == 2
    # Chronological: msg1 first, then msg2
    assert "Mijoz: Meni ishdan noqonuniy bo'shatishmoqchi" in lines[0]
    assert "Yurist (Bot): Mehnat kodeksining 161-moddasiga ko'ra" in lines[1]


@pytest.mark.asyncio
async def test_llm_service_includes_conversation_history_in_prompt():
    """Verify LLMService injects <conversation_history> into the prompt when provided."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        "Oldingi murojaatingizni inobatga olgan holda aytishim mumkinki...\n"
        "```json\n"
        '{"is_legal_case": true, "risk_level": "medium", "risk_score": 45, "upsell_offer": "", "cta_type": "consultation"}\n'
        "```"
    )
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    llm = LLMService(client=mock_client)
    question = "Ular menga tovon puli to'lashdan bosh tortishyapti"
    history = (
        "[2026-10-17 14:00] Mijoz: Meni ishdan bo'shatishmoqchi, korxona nomi 'Mega Stroy'\n"
        "[2026-10-17 14:01] Yurist (Bot): Ogohlantirish muddati 2 oy."
    )

    res = await llm.analyze_legal_inquiry(
        question=question,
        language="uz",
        conversation_history=history,
    )

    call_args = mock_client.aio.models.generate_content.call_args
    sent_prompt = call_args.kwargs.get("contents")

    # Verify conversation history tags and content are present
    assert "<conversation_history>" in sent_prompt
    assert "</conversation_history>" in sent_prompt
    assert "Mega Stroy" in sent_prompt
    assert "Ular menga tovon puli to'lashdan bosh tortishyapti" in sent_prompt
    assert res.is_legal_case is True
    assert res.risk_level == "medium"


@pytest.mark.asyncio
async def test_inquiry_service_fetches_and_passes_history():
    """Verify InquiryService loads history context and passes it to LLMService."""
    mock_llm = MagicMock(spec=LLMService)
    mock_llm.analyze_legal_inquiry = AsyncMock(
        return_value=LegalAnalysisResult(
            response_text="Huquqiy javob",
            risk_level="low",
            risk_score=20,
            is_legal_case=True,
            upsell_offer="",
            cta_type="none",
        )
    )

    mock_rag = MagicMock()
    mock_rag.search_relevant_laws = AsyncMock(return_value="Qonun moddasi")

    inquiry_service = InquiryService(llm_service=mock_llm, rag_service=mock_rag)

    session = AsyncMock()
    user = MagicMock(spec=User)
    user.id = 5
    user.telegram_id = 555
    user.language = "uz"
    user.free_questions_left = 3
    user.is_subscribed = False

    orig_get_history = ChatService.get_recent_history_context
    ChatService.get_recent_history_context = AsyncMock(
        return_value="[2026-10-17] Mijoz: Kechagi masala"
    )

    orig_decrement = UserService.decrement_question
    UserService.decrement_question = AsyncMock()

    try:
        _inquiry, analysis = await inquiry_service.process_text_inquiry(
            session=session,
            user=user,
            question_text="Bugungi savol",
        )
        assert mock_llm.analyze_legal_inquiry.called
        kwargs = mock_llm.analyze_legal_inquiry.call_args.kwargs
        assert kwargs["conversation_history"] == "[2026-10-17] Mijoz: Kechagi masala"
        assert kwargs["question"] == "Bugungi savol"
        assert analysis.response_text == "Huquqiy javob"
    finally:
        ChatService.get_recent_history_context = orig_get_history
        UserService.decrement_question = orig_decrement


@pytest.mark.asyncio
async def test_bot_settings_keyboard_clean():
    """Verify that the bot settings keyboard only contains language and referral buttons."""
    from app.bot.keyboards.keyboards import settings_kb

    kb = settings_kb("uz")
    # Should only have 2 buttons: Tilni o'zgartirish and Do'stlarni taklif qilish
    button_callbacks = [
        btn.callback_data for row in kb.inline_keyboard for btn in row if btn.callback_data
    ]
    assert button_callbacks == ["settings:change_lang", "settings:show_referral"]



@pytest.mark.asyncio
async def test_settings_api_debounce():
    """Verify GET and PUT /settings/bot endpoints handle inquiry_debounce_seconds."""
    from app.api.v1.settings import BotSettingsUpdate, get_bot_settings, update_bot_settings

    orig_val = settings.INQUIRY_DEBOUNCE_SECONDS
    settings.INQUIRY_DEBOUNCE_SECONDS = 3.0
    inquiry_debouncer.debounce_seconds = 3.0

    try:
        # GET
        res = await get_bot_settings()
        assert "inquiry_debounce_seconds" in res
        assert res["inquiry_debounce_seconds"] == 3.0

        # PUT
        update_payload = BotSettingsUpdate(inquiry_debounce_seconds=4.0)
        updated = await update_bot_settings(update_payload)
        assert updated["inquiry_debounce_seconds"] == 4.0
        assert inquiry_debouncer.debounce_seconds == 4.0
        assert settings.INQUIRY_DEBOUNCE_SECONDS == 4.0
    finally:
        inquiry_debouncer.debounce_seconds = orig_val
        settings.INQUIRY_DEBOUNCE_SECONDS = orig_val

