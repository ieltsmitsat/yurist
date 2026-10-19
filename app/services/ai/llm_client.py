import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types
from openai.types.chat import ChatCompletionMessageParam

from app.core.config import settings
from app.services.ai.pii_masker import PIIMasker
from app.services.ai.prompts import PromptManager
from app.utils.text import adjust_greeting, normalize_uzbek_text

logger = logging.getLogger(__name__)


@dataclass
class LegalAnalysisResult:
    response_text: str
    risk_level: str  # none, low, medium, high
    risk_score: int  # 0-100
    upsell_offer: str
    cta_type: str  # none, consultation, audit, court, claim, business
    is_legal_case: bool = True


def detect_service_cta_from_question(question: str) -> str:
    """Heuristic detector mapping question subject to legal service type."""
    q = question.lower()

    # Audit / Shartnoma tekshirish
    if any(k in q for k in ["shartnoma", "dogovor", "kontrakt", "ijara", "oldi-sotdi", "ekspertiza", "hujjat tahlili"]):
        return "audit"

    # Claim / Da'vo arizasi / Talabnoma / Qarz undirish
    if any(k in q for k in ["da'vo", "davo", "ariza", "talabnoma", "qarz", "undirish", "pulimni", "qoplash", "zarar", "aliment", "pretenz", "isk"]):
        return "claim"

    # Court / Sud majlisi / Himoya
    if any(k in q for k in ["sud", "sudya", "prokuror", "tergov", "iib", "militsiya", "jinoyat", "mahkama", "apellats", "kassats"]):
        return "court"

    # Business / MChJ / Korxona
    if any(k in q for k in ["mchj", "ooo", "firma", "biznes", "korxona", "yatt", "tadbirkor", "soliq", "ta'sischi", "ulush"]):
        return "business"

    return "consultation"


class LLMService:
    """Manages AI legal generation and structuring with human emulation."""

    def __init__(self, client: Any | None = None) -> None:
        if client is not None:
            self.client = client
        else:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def _generate_text(
        self,
        prompt: str,
        system_instruction: str,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Execute text generation with Google Gemini or mock/fallback client."""
        # Compatibility with OpenAI-like client
        if hasattr(self.client, "chat") and not hasattr(self.client, "aio"):
            messages: list[ChatCompletionMessageParam] = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ]
            resp = await self.client.chat.completions.create(
                model=model or settings.LLM_MODEL,
                messages=messages,
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""

        # Google Gemini client
        target_model = model or settings.GEMINI_MODEL
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        # Hardcoded reliable models first, then dynamic config models as fallback
        models_to_try = [
            "gemini-3.5-flash-lite",  # Most reliable as of Oct 2026
            target_model,
            settings.GEMINI_FALLBACK_MODEL,
            "gemini-3.1-flash-lite",
        ]
        seen: set[str] = set()
        unique_models: list[str] = []
        for m in models_to_try:
            if m and m not in seen:
                seen.add(m)
                unique_models.append(m)

        last_error: Exception | None = None
        for mod in unique_models:
            for attempt in range(3):
                try:
                    response = await self.client.aio.models.generate_content(
                        model=mod,
                        contents=prompt,
                        config=config,
                    )
                    if response and response.text:
                        logger.info("Model %s succeeded on attempt %d.", mod, attempt + 1)
                        return str(response.text)
                except Exception as e:  # noqa: BLE001
                    last_error = e
                    err_str = str(e).lower()
                    logger.warning(
                        "Model %s (attempt %d) failed (%s).",
                        mod,
                        attempt + 1,
                        e,
                    )
                    # Skip model entirely on 404 / deprecated
                    if "404" in err_str or "not found" in err_str or "no longer available" in err_str:
                        break
                    # Exponential backoff on 503 (1s, 2s, 4s)
                    await asyncio.sleep(min(2 ** attempt, 4))

        # Optional OpenAI fallback if configured
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "dummy_openai_key":
            try:
                from openai import AsyncOpenAI

                openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ]
                resp = await openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=temperature,
                )
                if resp.choices and resp.choices[0].message.content:
                    logger.info("Successfully used OpenAI fallback for legal response")
                    return str(resp.choices[0].message.content)
            except Exception as e:  # noqa: BLE001
                logger.error("OpenAI fallback also failed: %s", e)

        raise RuntimeError(f"All Gemini models failed to generate response. Last error: {last_error}")

    async def analyze_legal_inquiry(
        self,
        question: str,
        language: str = "uz",
        rag_context: str | None = None,
        conversation_history: str | None = None,
    ) -> LegalAnalysisResult:
        """Generate humanlike lawyer response and risk scoring for client inquiry."""
        system_prompt = PromptManager.get("PERSONA_SYSTEM_PROMPT_UZ") if language == "uz" else PromptManager.get("PERSONA_SYSTEM_PROMPT_RU")

        # Local PII Redaction before sending to LLM (OWASP security-pii-masker rule)
        sanitized_question = PIIMasker.redact_financial(question)

        content_parts: list[str] = []
        if conversation_history:
            content_parts.append(f"<conversation_history>\n{conversation_history}\n</conversation_history>")

        if conversation_history:
            current_prefix = "Mijozning joriy murojaati:\n" if language == "uz" else "Текущее обращение клиента:\n"
            content_parts.append(f"{current_prefix}{sanitized_question}")
        else:
            content_parts.append(sanitized_question)

        if rag_context:
            content_parts.append(f"<legal_context>\n{rag_context}\n</legal_context>")

        user_content = "\n\n".join(content_parts)

        format_instruction = (
            "\n\nMUHIM QOIDALAR:\n"
            "- Agar mijoz o'z xabarida 'Assalomu alaykum' deb salom bermagan bo'lsa (to'g'ridan-to'g'ri savol bergan bo'lsa), javobni 'Assalomu alaykum' yoki boshqa salomlashish bilan QAT'IYAN BOSHLAMANG! Hech qanday salom bermasdan to'g'ridan-to'g'ri huquqiy javobga o'ting.\n"
            "- FAQAT VA FAQAT mijoz o'z xabarida 'Assalomu alaykum' deb salom bergan bo'lsa, javobni 'Assalomu alaykum, yaxshimisiz! ...' deb boshlang.\n"
            "- Suhbat tarixi (<conversation_history>) faqat passiv ma'lumotnoma: mijozdan avvalgi ishlari haqida o'zingizdan o'zingiz so'ramang. Faqat mijoz o'zi so'rasa o'sha kontekstdan foydalaning.\n"
            "- Xizmat takliflarida 'kafolat' so'zini ishlatmang.\n"
            "- Mijozning xabariga faqat qisqa va lo'nda javob yozing. Matn ichida 'Xavf darajasi' yoki 'Xulosa' so'zlarini MUTLAQO yozmang!\n\n"
            "Javobingiz oxirida alohida JSON formatidagi blokni QUYIDAGI ko'rinishda yozing:\n"
            "```json\n"
            "{\n"
            '  "is_legal_case": true | false,\n'
            '  "risk_level": "none" | "low" | "medium" | "high",\n'
            '  "risk_score": 0-100,\n'
            '  "upsell_offer": "Mijozga taklif qilinadigan xizmat matni yoki bo\'sh",\n'
            '  "cta_type": "consultation" | "audit" | "court" | "claim" | "business" | "none"\n'
            "}\n"
            "```\n"
            "cta_type tanlash qoidalari:\n"
            "- Shartnomalar, ijara, oldi-sotdi, hujjat tekshirish: 'audit'\n"
            "- Qarz undirish, sudga da'vo arizasi, talabnoma tuzish, zarar qoplash, aliment: 'claim'\n"
            "- Sud majlisi, tergov, sudda himoya yoki vakillik: 'court'\n"
            "- Biznes, MChJ, soliq, korxona va tadbirkorlik masalalari: 'business'\n"
            "- Boshqa shaxsiy yoki umumiy yuridik savollar: 'consultation'\n"
            "- Faqat salomlashish yoki nohuquqiy xabar: 'none'\n"
        )
        if language == "ru":
            format_instruction = (
                "\n\nВАЖНЫЕ ПРАВИЛА:\n"
                "- Если клиент в своем сообщении не поздоровался, КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО начинать ответ со слова «Здравствуйте» или «Добрый день»! Сразу отвечайте по существу.\n"
                "- ТОЛЬКО если клиент сам первым поздоровался в своем сообщении, начните ответ со слова «Здравствуйте! ...».\n"
                "- История переписки (<conversation_history>) служит исключительно пассивной памятью: сами не расспрашивайте о прошлых делах клиента, используйте контекст только если клиент сам о них спросил.\n"
                "- Не используйте слово «гарантия» при предложении услуг.\n"
                "- Пишите только краткий текстовый ответ. В самом тексте КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать слова 'Уровень риска' или 'Вывод'!\n\n"
                "В самом конце ответа добавьте блок JSON строго в следующем формате:\n"
                "```json\n"
                "{\n"
                '  "is_legal_case": true | false,\n'
                '  "risk_level": "none" | "low" | "medium" | "high",\n'
                '  "risk_score": 0-100,\n'
                '  "upsell_offer": "Текст предлагаемой услуги или пусто",\n'
                '  "cta_type": "consultation" | "audit" | "court" | "claim" | "business" | "none"\n'
                "}\n"
                "```\n"
                "Правила выбора cta_type:\n"
                "- Договоры, аренда, купля-продажа, экспертиза документов: 'audit'\n"
                "- Взыскание долга, исковое заявление, досудебная претензия, алименты: 'claim'\n"
                "- Судебное заседание, следствие, защита в суде: 'court'\n"
                "- Бизнес, ООО, налоги, корпоративные вопросы: 'business'\n"
                "- Другие личные или общие юридические вопросы: 'consultation'\n"
                "- Приветствие или неюридический вопрос: 'none'\n"
            )

        full_system = system_prompt + format_instruction
        raw_text = await self._generate_text(
            prompt=user_content,
            system_instruction=full_system,
            model=settings.GEMINI_MODEL,
            temperature=0.35,
        )
        return self._parse_structured_response(raw_text, language, question=sanitized_question)

    async def analyze_express_audit(
        self,
        document_text: str,
        language: str = "uz",
    ) -> LegalAnalysisResult:
        """Run express legal audit on a contract or court notice."""
        system_prompt = PromptManager.get("EXPRESS_AUDIT_PROMPT_UZ") if language == "uz" else PromptManager.get("EXPRESS_AUDIT_PROMPT_RU")

        # Truncate and sanitize PII before LLM submission
        truncated_doc = PIIMasker.redact_financial(document_text)
        if len(truncated_doc) > 100_000:
            logger.warning(
                "Document text exceeds 100k chars (%d); truncating for audit",
                len(truncated_doc),
            )
            truncated_doc = truncated_doc[:100_000]

        format_instruction = (
            "\n\nMUHIM: Xulosani qisqa, lo'nda va faqat eng muhim 2 ta zaiflik bilan taqdim eting (maksimal 120 so'z).\n\n"
            "Javobingiz oxirida alohida JSON formatidagi blokni QUYIDAGI ko'rinishda yozing:\n"
            "```json\n"
            "{\n"
            '  "risk_level": "low" | "medium" | "high",\n'
            '  "risk_score": 0-100,\n'
            '  "upsell_offer": "To\'liq audit xizmatining taklifi",\n'
            '  "cta_type": "audit"\n'
            "}\n"
            "```"
        )
        if language == "ru":
            format_instruction = (
                "\n\nВ конце добавьте блок JSON:\n"
                "```json\n"
                "{\n"
                '  "risk_level": "low" | "medium" | "high",\n'
                '  "risk_score": 0-100,\n'
                '  "upsell_offer": "Предложение полного аудита",\n'
                '  "cta_type": "audit"\n'
                "}\n"
                "```"
            )

        full_system = system_prompt + format_instruction
        prompt = f"Hujjat matni:\n\n{truncated_doc}"
        raw_text = await self._generate_text(
            prompt=prompt,
            system_instruction=full_system,
            model=settings.GEMINI_MODEL,
            temperature=0.3,
        )
        return self._parse_structured_response(raw_text, language)

    async def generate_retargeting_followup(
        self,
        inquiry_summary: str,
        language: str = "uz",
        hours_passed: int = 24,
    ) -> str:
        """Generate a warm, friendly follow-up message from the lawyer regarding deadlines."""
        safe_summary = PIIMasker.redact_financial(inquiry_summary)
        if language == "uz":
            prompt = (
                f"Siz huquqshunossiz. Mijoz {hours_passed} soat oldin quyidagi masala bo'yicha yozgan edi: '{safe_summary}'.\n"
                "Mijoz hali konsultatsiyaga yozilmadi yoki ishni davom ettirmadi.\n"
                "Unga samimiy, insoniy tarzda eslatma yozing: qonunchilikdagi muddatlar o'tib ketishi xavfi borligini va "
                "masalani kechiktirmay birgalikda ko'rib chiqish maqsadga muvofiqligini ayting. Qisqa, 2-3 ta gap."
            )
            system_prompt = PromptManager.get("PERSONA_SYSTEM_PROMPT_UZ")
        else:
            prompt = (
                f"Вы юрист. Клиент {hours_passed} ч. назад обращался с вопросом: '{inquiry_summary}'.\n"
                "Клиент еще не записался на консультацию. Напишите теплое, ненавязчивое напоминание от первого лица "
                "о процессуальных сроках и важности своевременных действий. Кратко, 2-3 предложения."
            )
            system_prompt = PromptManager.get("PERSONA_SYSTEM_PROMPT_RU")

        raw_text = await self._generate_text(
            prompt=prompt,
            system_instruction=system_prompt,
            model=settings.GEMINI_FALLBACK_MODEL,
            temperature=0.5,
        )
        result_text = raw_text.strip()
        if language == "uz":
            result_text = normalize_uzbek_text(result_text)
        return result_text

    def _parse_structured_response(
        self, raw_text: str, language: str, question: str = ""
    ) -> LegalAnalysisResult:
        """Extract response text and trailing JSON metadata block."""
        risk_level = "medium"
        risk_score = 50
        upsell_offer = (
            "Shaxsiy huquqshunos maslahatiga yozilishni tavsiya qilaman."
            if language == "uz"
            else "Рекомендую записаться на индивидуальную консультацию."
        )
        cta_type = "consultation"
        is_legal_case = True

        response_body = raw_text

        if "```json" in raw_text:
            parts = raw_text.split("```json")
            response_body = parts[0].strip()
            json_block = parts[1].split("```")[0].strip()
            try:
                data = json.loads(json_block)
                if "is_legal_case" in data:
                    is_legal_case = bool(data["is_legal_case"])
                risk_level = data.get("risk_level", risk_level)
                risk_score = int(data.get("risk_score", risk_score))
                upsell_offer = data.get("upsell_offer", upsell_offer)
                cta_type = data.get("cta_type", cta_type)
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.warning("Could not parse JSON block from LLM: %s", e)

        # Normalize risk_level
        if risk_level not in ("none", "low", "medium", "high"):
            risk_level = "medium"

        # Validate and dynamically infer cta_type from question if default
        if cta_type not in ("none", "consultation", "audit", "court", "claim", "business"):
            cta_type = "consultation"

        if is_legal_case and question and (cta_type == "consultation" or not cta_type):
            detected = detect_service_cta_from_question(question)
            if detected != "consultation":
                cta_type = detected

        # Always clean any accidental risk lines from the visible text
        lines = [
            line
            for line in response_body.splitlines()
            if not any(
                line.strip().lower().startswith(prefix)
                for prefix in (
                    "xavf darajasi",
                    "уровень риска",
                    "xulosa:",
                    "вывод:",
                    "qonuniy oqibatlari",
                    "юридические последствия",
                    "yechim:",
                    "решение:",
                )
            )
        ]
        response_body = "\n".join(lines).strip()

        if language == "uz":
            response_body = normalize_uzbek_text(response_body)
            upsell_offer = normalize_uzbek_text(upsell_offer)

        if question:
            response_body = adjust_greeting(response_body, question=question, language=language)

        if not is_legal_case or risk_level == "none":
            risk_level = "none"
            risk_score = 0
            cta_type = "none"
            is_legal_case = False

        return LegalAnalysisResult(
            response_text=response_body,
            risk_level=risk_level,
            risk_score=min(max(risk_score, 0), 100),
            upsell_offer=upsell_offer,
            cta_type=cta_type,
            is_legal_case=is_legal_case,
        )
