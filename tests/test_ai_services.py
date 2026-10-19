"""Tests for AI services: Prompts, LLM client, Document parsing, Speech, and RAG."""

import io
from unittest.mock import AsyncMock, MagicMock

import pytest
from docx import Document

from app.services.ai.document import DocumentParser
from app.services.ai.llm_client import LegalAnalysisResult, LLMService
from app.services.ai.rag import RAGService
from app.services.ai.speech import SpeechService


def test_document_parser_docx():
    # Create in-memory docx
    doc = Document()
    doc.add_heading("IJARA SHARTNOMASI", level=1)
    doc.add_paragraph("1.1. Ijaraga beruvchi xonadonni ijaraga beradi.")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Narx"
    table.rows[0].cells[1].text = "500 USD"

    buffer = io.BytesIO()
    doc.save(buffer)
    docx_bytes = buffer.getvalue()

    text = DocumentParser.extract_text("shartnoma.docx", docx_bytes)
    assert "IJARA SHARTNOMASI" in text
    assert "1.1. Ijaraga beruvchi" in text
    assert "Narx | 500 USD" in text


def test_document_parser_txt():
    txt_bytes = b"Sud qaroriga nisbatan apellyatsiya shikoyati"
    text = DocumentParser.extract_text("shikoyat.txt", txt_bytes)
    assert "apellyatsiya shikoyati" in text


def test_document_parser_invalid_ext():
    with pytest.raises(ValueError, match="Qo'llab-quvvatlanmaydigan fayl formati"):
        DocumentParser.extract_text("virus.exe", b"fake binary data")


def test_llm_service_structured_parsing():
    llm = LLMService(client=None)

    raw_response = (
        "Assalomu alaykum! Sizning meros bo'yicha masalangizni ko'rib chiqdim.\n\n"
        "O'zbekiston Respublikasi Fuqarolik kodeksining 1134-moddasiga ko'ra, "
        "meros ochilgan kundan e'tiboran 6 oy ichida merosni qabul qilib olishingiz shart.\n\n"
        "🟢 Past xavf: Muddat hali o'tib ketmagan bo'lsa, xavf kam.\n\n"
        "```json\n"
        "{\n"
        '  "risk_level": "low",\n'
        '  "risk_score": 25,\n'
        '  "upsell_offer": "Notarial idoraga taqdim etiladigan arizani tayyorlab berishimiz mumkin.",\n'
        '  "cta_type": "consultation"\n'
        "}\n"
        "```"
    )

    result = llm._parse_structured_response(raw_response, language="uz")
    assert isinstance(result, LegalAnalysisResult)
    assert result.risk_level == "low"
    assert result.risk_score == 25
    assert "1134-moddasiga ko'ra" in result.response_text
    assert "```json" not in result.response_text
    assert "Notarial idoraga taqdim etiladigan" in result.upsell_offer
    assert result.cta_type == "consultation"


def test_llm_service_fallback_parsing():
    llm = LLMService(client=None)

    # When LLM does not return any json block
    raw_response = "Bu oddiy yuridik javob matni bo'lib, json bloki yo'q."
    result = llm._parse_structured_response(raw_response, language="uz")
    assert result.risk_level == "medium"
    assert result.risk_score == 50
    assert result.response_text == raw_response


def test_llm_service_casual_chat_parsing_strips_risk():
    llm = LLMService(client=None)

    raw_response = (
        "Assalomu alaykum! Ismim Aziz, advokatman. Sizga qanday yordam bera olaman?\n\n"
        "Xavf darajasi: 🟢 Past xavf.\n"
        "Xulosa: Muammoni ayting.\n"
        "```json\n"
        "{\n"
        '  "is_legal_case": false,\n'
        '  "risk_level": "none",\n'
        '  "risk_score": 0,\n'
        '  "upsell_offer": "",\n'
        '  "cta_type": "none"\n'
        "}\n"
        "```"
    )
    result = llm._parse_structured_response(raw_response, language="uz")
    assert result.is_legal_case is False
    assert result.risk_level == "none"
    assert result.risk_score == 0
    assert result.cta_type == "none"
    assert "Xavf darajasi" not in result.response_text
    assert "Xulosa:" not in result.response_text
    assert "Ismim Aziz" in result.response_text


@pytest.mark.asyncio
async def test_llm_service_gemini_inquiry_generation():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        "Hurmatli fuqaro, sizning masalangiz yuzasidan quyidagilarni ma'lum qilaman.\n"
        "```json\n"
        '{"risk_level": "high", "risk_score": 85, "upsell_offer": "Advokat bilan shoshilinch uchrashuv", "cta_type": "court"}\n'
        "```"
    )
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    llm = LLMService(client=mock_client)
    res = await llm.analyze_legal_inquiry("Meni nohaq ishdan bo'shatishdi", language="uz")

    assert res.risk_level == "high"
    assert res.risk_score == 85
    assert res.cta_type == "court"
    assert "Hurmatli fuqaro" in res.response_text


@pytest.mark.asyncio
async def test_llm_service_retargeting_followup():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Assalomu alaykum, da'vo muddatini o'tkazib yubormaslik uchun bog'laning."
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    llm = LLMService(client=mock_client)
    text = await llm.generate_retargeting_followup("Meros masalasi", language="uz")
    assert "da'vo muddatini" in text


@pytest.mark.asyncio
async def test_speech_service_missing_file():
    speech = SpeechService(client=None)
    with pytest.raises(FileNotFoundError):
        await speech.transcribe_audio("non_existent_file.ogg")


@pytest.mark.asyncio
async def test_speech_service_transcribe_mock(tmp_path):
    dummy_audio = tmp_path / "voice.ogg"
    dummy_audio.write_bytes(b"dummy ogg bytes")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Mening aliment bo'yicha savolim bor edi"
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    speech = SpeechService(client=mock_client)
    text = await speech.transcribe_audio(dummy_audio, language="uz")
    assert text == "Mening aliment bo'yicha savolim bor edi"


@pytest.mark.asyncio
async def test_rag_service_gemini_embedding_mock():
    mock_client = MagicMock()
    mock_res = MagicMock()
    mock_item = MagicMock()
    mock_item.values = [0.1] * 1536
    mock_res.embeddings = [mock_item]
    mock_client.aio.models.embed_content = AsyncMock(return_value=mock_res)

    rag = RAGService(client=mock_client)
    embedding = await rag.get_embedding("Mehnat nizolari")
    assert len(embedding) == 1536
    assert embedding[0] == 0.1


def test_pii_masker_redaction():
    from app.services.ai.pii_masker import PIIMasker

    text = (
        "Mening pasportim AA 1234567, telefonim +998901234567, "
        "PINFL 31234567890123 va kartam 8600 1234 5678 9012. "
        "O'zbekiston Mehnat kodeksining 161-moddasi bo'yicha yordam bering."
    )
    redacted = PIIMasker.redact(text)
    assert "[PASSPORT_REDACTED]" in redacted
    assert "[PHONE_REDACTED]" in redacted
    assert "[PINFL_REDACTED]" in redacted
    assert "[CARD_REDACTED]" in redacted
    assert "161-moddasi" in redacted


@pytest.mark.asyncio
async def test_llm_service_with_pii_and_rag_context():
    from app.services.ai.llm_client import LLMService

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        "Hurmatli mijoz, vaziyatingizni o'rgandim.\n"
        "```json\n"
        '{"risk_level": "medium", "risk_score": 50, "upsell_offer": "Konsultatsiya", "cta_type": "consultation"}\n'
        "```"
    )
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    llm = LLMService(client=mock_client)
    # Legal PII (phone, passport) must be preserved for accurate legal advice;
    # only financial data (credit cards) should be redacted.
    question = "Mening raqamim +998901112233, pasportim AB 7654321, kartam 8600 1234 5678 9012."
    rag_context = "Mehnat kodeksi 161-modda: Ish beruvchi tashabbusi bilan bekor qilish."
    res = await llm.analyze_legal_inquiry(question, language="uz", rag_context=rag_context)

    # Check mock call contents
    call_args = mock_client.aio.models.generate_content.call_args
    sent_prompt = call_args.kwargs.get("contents")
    # Legal PII is preserved (not redacted)
    assert "+998901112233" in sent_prompt
    assert "AB 7654321" in sent_prompt
    # Financial data is redacted
    assert "[CARD_REDACTED]" in sent_prompt
    assert "8600 1234 5678 9012" not in sent_prompt
    # RAG context is injected
    assert "<legal_context>" in sent_prompt
    assert "</legal_context>" in sent_prompt
    assert res.risk_level == "medium"


def test_greeting_adjustment_rules():
    from app.utils.text import adjust_greeting, has_user_greeting

    # 1. has_user_greeting tests
    assert has_user_greeting("Assalomu alaykum, aliment haqida savol") is True
    assert has_user_greeting("assalomualaykum") is True
    assert has_user_greeting("Assalomu aleykum!") is True
    assert has_user_greeting("salom") is True
    assert has_user_greeting("Ассалому алайкум") is True
    assert has_user_greeting("Menga aliment to'lashmayapti") is False
    assert has_user_greeting("Shartnomani bekor qilish tartibi qanday?") is False
    assert has_user_greeting("Здравствуйте, вопрос по иску", language="ru") is True
    assert has_user_greeting("Вопрос по иску", language="ru") is False

    # 2. adjust_greeting when user did NOT greet -> greeting must be stripped
    raw_with_greet = "Assalomu alaykum! Mehnat kodeksiga ko'ra siz ishdan asossiz bo'shatilgansiz."
    q_no_greet = "Meni ishdan bo'shatishdi, nima qilsam bo'ladi?"
    res_no_greet = adjust_greeting(raw_with_greet, question=q_no_greet, language="uz")
    assert not res_no_greet.lower().startswith("assalomu alaykum")
    assert res_no_greet.startswith("Mehnat kodeksiga ko'ra")

    # 3. adjust_greeting when user DID greet -> must start with 'Assalomu alaykum, yaxshimisiz!'
    q_with_greet = "Assalomu alaykum, meni ishdan bo'shatishdi"
    res_with_greet = adjust_greeting(raw_with_greet, question=q_with_greet, language="uz")
    assert res_with_greet.startswith("Assalomu alaykum, yaxshimisiz!")
    assert "Mehnat kodeksiga ko'ra" in res_with_greet

    # 4. Russian: adjust_greeting when user did NOT greet -> strip greeting
    raw_ru_greet = "Здравствуйте! Согласно Трудовому кодексу вы имеете право на компенсацию."
    q_ru_no_greet = "Меня уволили без компенсации"
    res_ru_no = adjust_greeting(raw_ru_greet, question=q_ru_no_greet, language="ru")
    assert not res_ru_no.lower().startswith("здравствуйте")
    assert res_ru_no.startswith("Согласно Трудовому кодексу")

    # 5. Russian: adjust_greeting when user DID greet -> starts with Здравствуйте!
    q_ru_with_greet = "Здравствуйте, меня уволили"
    res_ru_with = adjust_greeting(raw_ru_greet, question=q_ru_with_greet, language="ru")
    assert res_ru_with.startswith("Здравствуйте!")



