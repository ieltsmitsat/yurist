"""Tests for database models and configuration."""


from app.core.config import settings
from app.core.redis import BusinessPauseManager
from app.db.models import (
    Inquiry,
    LegalChunk,
    Service,
    User,
)


def test_settings_loaded():
    assert settings.PROJECT_NAME == "Yurist LegalTech AI Bot"
    assert settings.FREE_QUESTIONS_LIMIT >= 1
    assert settings.BUSINESS_TAKEOVER_PAUSE_SECONDS == 1800


def test_user_model_instantiation():
    user = User(
        telegram_id=123456789,
        full_name="Alisher Navoiy",
        phone_number="+998901234567",
        language="uz",
        referral_code="REF123",
        free_questions_left=3,
    )
    assert user.telegram_id == 123456789
    assert user.language == "uz"
    assert user.free_questions_left == 3
    assert user.lead_status == "new"


def test_service_model_instantiation():
    service = Service(
        title_uz="Sudda vakillik",
        title_ru="Представительство в суде",
        price="1 500 000 so'm",
        service_type="court",
    )
    assert service.title_uz == "Sudda vakillik"
    assert service.price == "1 500 000 so'm"
    assert service.is_active is True


def test_inquiry_and_risk_scoring():
    inquiry = Inquiry(
        user_id=1,
        question_text="Meros masalasi bo'yicha nizo",
        risk_level="high",
        risk_score=85,
    )
    assert inquiry.risk_level == "high"
    assert inquiry.risk_score == 85
    assert inquiry.status == "answered"


def test_legal_chunk_model():
    chunk = LegalChunk(
        law_title="Fuqarolik kodeksi",
        article_number="356-modda",
        chunk_text="Shartnoma tushunchasi va shartlari...",
        lex_url="https://lex.uz/docs/111189",
    )
    assert chunk.law_title == "Fuqarolik kodeksi"
    assert chunk.article_number == "356-modda"


class MockRedis:
    def __init__(self):
        self.data = {}

    async def set(self, key, value, ex=None):
        self.data[key] = value

    async def get(self, key):
        return self.data.get(key)

    async def delete(self, key):
        self.data.pop(key, None)


async def test_business_pause_manager():
    mock_redis = MockRedis()
    chat_id = 987654321

    # Initially not paused
    assert await BusinessPauseManager.is_paused(chat_id, mock_redis) is False

    # Lawyer sends message -> set paused
    await BusinessPauseManager.set_paused(chat_id, mock_redis, duration_seconds=1800)
    assert await BusinessPauseManager.is_paused(chat_id, mock_redis) is True

    # Resume
    await BusinessPauseManager.resume(chat_id, mock_redis)
    assert await BusinessPauseManager.is_paused(chat_id, mock_redis) is False
