"""Comprehensive test suite for all 9 Instagram DM Automation skills and Webhook API."""

import time
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.main import create_app
from app.core.redis import InMemoryRedisClient
from app.services.instagram.audio_stt import MultimodalVoiceDMSkill
from app.services.instagram.comment_to_dm import CommentToDMSkill
from app.services.instagram.contact_capture import ContactCapture24hSkill
from app.services.instagram.human_handoff import HumanAgentHandoffSkill
from app.services.instagram.intake_triage import LegalCategory, LegalIntakeTriageSkill, RiskLevel
from app.services.instagram.lead_conversion import LeadConversionSkill
from app.services.instagram.lexuz_rag import LexUzRAGSkill
from app.services.instagram.persona import UndetectablePersonaSkill
from app.services.instagram.policy_enforcer import MetaPolicyEnforcerSkill


@pytest.fixture
def mock_redis() -> InMemoryRedisClient:
    return InMemoryRedisClient()


# ---------------------------------------------------------------------------
# Skill 1: Comment-to-DM Trigger
# ---------------------------------------------------------------------------
def test_skill_comment_to_dm_matching() -> None:
    skill = CommentToDMSkill()
    assert skill.matches_comment("Menga sud masalasida yordam kerak!") is True
    assert skill.matches_comment("Chiroyli rasm ekan rahmat") is False

    keywords = skill.extract_matched_keywords("Advokat kerak, shartnoma buzildi")
    assert "advokat" in keywords
    assert "shartnoma" in keywords


@pytest.mark.asyncio
async def test_skill_comment_to_dm_rate_limiting(mock_redis: InMemoryRedisClient) -> None:
    skill = CommentToDMSkill()
    comment_id = "comm_12345"

    assert await skill.can_send_private_reply(comment_id, mock_redis) is True
    await skill.mark_reply_sent(comment_id, mock_redis)
    # Cannot send twice to the same comment
    assert await skill.can_send_private_reply(comment_id, mock_redis) is False


def test_skill_comment_to_dm_payload() -> None:
    skill = CommentToDMSkill()
    payload = skill.build_private_reply_payload("comm_999")
    assert "/comm_999/private_replies" in payload["endpoint"]
    assert "Direct" in payload["body"]["message"]


# ---------------------------------------------------------------------------
# Skill 2: 24h Window & Contact Capture
# ---------------------------------------------------------------------------
def test_skill_24h_contact_capture_window() -> None:
    now = ContactCapture24hSkill.get_current_utc_timestamp()
    assert ContactCapture24hSkill.is_window_active(now - 3600) is True  # 1 hour ago
    assert ContactCapture24hSkill.is_window_active(now - 90000) is False  # 25 hours ago

    # 22.5 hours ago -> should send warning
    assert ContactCapture24hSkill.should_send_closing_warning(now - (22.5 * 3600)) is True
    # 5 hours ago -> should not send warning yet
    assert ContactCapture24hSkill.should_send_closing_warning(now - (5 * 3600)) is False


def test_skill_24h_contact_capture_phone_extraction() -> None:
    assert ContactCapture24hSkill.extract_uz_phone("Mening raqamim +998901234567") == "+998901234567"
    assert ContactCapture24hSkill.extract_uz_phone("tel: 998 93 987-65-43") == "+998939876543"
    assert ContactCapture24hSkill.extract_uz_phone("nomer: 94 555 44 33") == "+998945554433"
    assert ContactCapture24hSkill.extract_uz_phone("telefonim yo'q hozircha") is None


# ---------------------------------------------------------------------------
# Skill 3: Undetectable Legal AI Persona
# ---------------------------------------------------------------------------
def test_skill_undetectable_persona() -> None:
    skill = UndetectablePersonaSkill()
    assert skill.is_personal_question("Necha yoshdasiz?") is True
    assert skill.is_personal_question("Qayerda yashaysiz, oilangiz bormi?") is True
    assert skill.is_personal_question("Shartnomani qanday bekor qilsa bo'ladi?") is False

    refusal_uz = skill.get_personal_question_response("Necha yoshdasiz?")
    assert "Afsusku shaxsiy savollaringizga javob bera olmayman" in refusal_uz

    refusal_ru = skill.get_personal_question_response("Сколько вам лет?")
    assert "К сожалению, я не отвечаю на личные вопросы" in refusal_ru

    # Sanitization
    leaked_text = "Men sun'iy intellekt sifatida yordam beraman."
    assert skill.contains_prohibited_tokens(leaked_text) is True
    sanitized = skill.sanitize_outbound_text(leaked_text)
    assert "sun'iy intellekt" not in sanitized.lower()


# ---------------------------------------------------------------------------
# Skill 4: Legal Intake, Triage & Risk Level Scoring
# ---------------------------------------------------------------------------
def test_skill_legal_intake_triage() -> None:
    skill = LegalIntakeTriageSkill()

    cat_family = skill.detect_category("Erim aliment to'lamayapti, ajrashishmoqchimiz")
    assert cat_family == LegalCategory.FAMILY

    cat_crim = skill.detect_category("Prokuraturadan chaqiruv qog'ozi keldi, tergovchi so'roq qilmoqchi")
    assert cat_crim == LegalCategory.CRIMINAL

    # Risk score & action strategy
    score_crit, level_crit = skill.calculate_risk_score("Hibsga olishdi, advokat kerak tezda!")
    assert level_crit == RiskLevel.CRITICAL
    assert score_crit >= 86
    strat_crit = skill.determine_action_strategy(level_crit)
    assert strat_crit["include_sos_instructions"] is True

    _score_low, level_low = skill.calculate_risk_score("Shartnoma tuzish haqida ma'lumot bering")
    assert level_low == RiskLevel.LOW
    strat_low = skill.determine_action_strategy(level_low)
    assert strat_low["offer_free_info"] is True


# ---------------------------------------------------------------------------
# Skill 5: Lex.uz RAG & Legal Retrieval
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_skill_lexuz_rag() -> None:
    skill = LexUzRAGSkill()
    citation = skill.format_citation("Fuqarolik Kodeksi", "354-modda")
    assert "O'zbekiston Respublikasi Fuqarolik Kodeksining 354-moddasiga muvofiq" in citation

    articles = await skill.retrieve_top_articles("Aliment undirish bo'yicha")
    assert len(articles) > 0
    context = skill.build_rag_context_block(articles)
    assert "<legal_context>" in context


# ---------------------------------------------------------------------------
# Skill 6: Multimodal Voice DM Processing
# ---------------------------------------------------------------------------
def test_skill_multimodal_audio_stt() -> None:
    skill = MultimodalVoiceDMSkill()
    att_voice = {"type": "audio", "payload": {"url": "https://cdn.example.com/audio.m4a"}}
    att_text = {"type": "image", "payload": {"url": "https://cdn.example.com/img.png"}}

    assert skill.is_voice_attachment(att_voice) is True
    assert skill.is_voice_attachment(att_text) is False
    assert skill.extract_audio_url(att_voice) == "https://cdn.example.com/audio.m4a"


# ---------------------------------------------------------------------------
# Skill 7: Human Agent Handoff
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_skill_human_handoff(mock_redis: InMemoryRedisClient) -> None:
    skill = HumanAgentHandoffSkill()
    chat_id = "ig_user_444"

    assert await skill.is_ai_paused(chat_id, mock_redis) is False
    await skill.set_lawyer_takeover(chat_id, mock_redis, pause_seconds=1800)
    assert await skill.is_ai_paused(chat_id, mock_redis) is True

    await skill.resume_ai(chat_id, mock_redis)
    assert await skill.is_ai_paused(chat_id, mock_redis) is False

    # Message Tagging
    now = 100000.0
    # 30 hours ago (between 24h and 7d)
    assert skill.should_use_human_agent_tag(now - (30 * 3600), now) is True
    # 5 hours ago (within 24h)
    assert skill.should_use_human_agent_tag(now - (5 * 3600), now) is False

    payload = skill.build_outbound_payload("rec_1", "Hello", use_human_agent_tag=True)
    assert payload["messaging_type"] == "MESSAGE_TAG"
    assert payload["tag"] == "HUMAN_AGENT"


# ---------------------------------------------------------------------------
# Skill 8: Meta Policy & Payload Safety
# ---------------------------------------------------------------------------
def test_skill_meta_policy_enforcer() -> None:
    skill = MetaPolicyEnforcerSkill(max_bytes=100)

    short_msg = "Qisqa xabar"
    assert skill.split_message_if_exceeds_limit(short_msg) == [short_msg]

    long_msg = "Bu birinchi jumla. " * 15  # well over 100 bytes
    parts = skill.split_message_if_exceeds_limit(long_msg)
    assert len(parts) > 1
    for part in parts:
        assert len(part.encode("utf-8")) <= 100

    # SLA check
    is_compliant, _ = skill.check_sla_compliance(time.time() - 5.0)
    assert is_compliant is True


# ---------------------------------------------------------------------------
# Skill 9: Lead Qualification & High-Ticket Conversion
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_skill_lead_conversion(mock_redis: InMemoryRedisClient) -> None:
    skill = LeadConversionSkill()
    user_id = "ig_user_888"

    assert await skill.get_remaining_free_questions(user_id, mock_redis, default_limit=3) == 3
    await skill.decrement_free_question(user_id, mock_redis)
    assert await skill.get_remaining_free_questions(user_id, mock_redis, default_limit=3) == 2

    # Lead qualification
    assert skill.is_lead_qualified(has_phone=True, risk_score=50, interactions_count=1) is True
    assert skill.is_lead_qualified(has_phone=False, risk_score=10, interactions_count=1) is False

    exhausted_uz = skill.get_exhausted_limit_message(is_russian=False)
    assert "3 ta bepul dastlabki yuridik tahlil yakunlandi" in exhausted_uz


# ---------------------------------------------------------------------------
# Instagram Webhook API Endpoints (GET verification & POST events)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_instagram_webhook_endpoints(mock_redis: InMemoryRedisClient) -> None:
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # GET Verification Success
        resp = await client.get(
            "/api/v1/instagram/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "yurist_instagram_verify_token",
                "hub.challenge": "115599",
            },
        )
        assert resp.status_code == 200
        assert resp.text == "115599"

        # GET Verification Fail
        resp_bad = await client.get(
            "/api/v1/instagram/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "115599",
            },
        )
        assert resp_bad.status_code == 403

        # POST Events Processing
        webhook_body = {
            "object": "instagram",
            "entry": [
                {
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "id": "comment_999",
                                "text": "Menga advokat yordami kerak, iltimos bog'laning",
                            },
                        }
                    ],
                    "messaging": [
                        {
                            "sender": {"id": "ig_user_111"},
                            "message": {"text": "Assalomu alaykum, aliment bo'yicha savolim bor edi."},
                        }
                    ],
                }
            ],
        }

        with patch("app.api.v1.instagram.get_redis_client", return_value=mock_redis):
            post_resp = await client.post("/api/v1/instagram/webhook", json=webhook_body)
            assert post_resp.status_code == 200
            assert post_resp.json() == {"status": "ok"}
