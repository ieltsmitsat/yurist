"""Central facade orchestrating all 9 Instagram DM Automation skills."""

import logging
import time
from typing import Any

import httpx

from app.core.config import settings
from app.services.instagram.audio_stt import MultimodalVoiceDMSkill
from app.services.instagram.comment_to_dm import CommentToDMSkill
from app.services.instagram.contact_capture import ContactCapture24hSkill
from app.services.instagram.human_handoff import HumanAgentHandoffSkill
from app.services.instagram.intake_triage import LegalIntakeTriageSkill, RiskLevel
from app.services.instagram.lead_conversion import LeadConversionSkill
from app.services.instagram.lexuz_rag import LexUzRAGSkill
from app.services.instagram.persona import UndetectablePersonaSkill
from app.services.instagram.policy_enforcer import MetaPolicyEnforcerSkill

logger = logging.getLogger(__name__)


class InstagramAutomationService:
    """Orchestrates all 9 Instagram DM and Comment Automation skills."""

    def __init__(
        self,
        comment_skill: CommentToDMSkill | None = None,
        contact_skill: ContactCapture24hSkill | None = None,
        persona_skill: UndetectablePersonaSkill | None = None,
        triage_skill: LegalIntakeTriageSkill | None = None,
        rag_skill: LexUzRAGSkill | None = None,
        voice_skill: MultimodalVoiceDMSkill | None = None,
        handoff_skill: HumanAgentHandoffSkill | None = None,
        policy_skill: MetaPolicyEnforcerSkill | None = None,
        conversion_skill: LeadConversionSkill | None = None,
    ) -> None:
        self.comment_skill = comment_skill or CommentToDMSkill()
        self.contact_skill = contact_skill or ContactCapture24hSkill()
        self.persona_skill = persona_skill or UndetectablePersonaSkill()
        self.triage_skill = triage_skill or LegalIntakeTriageSkill()
        self.rag_skill = rag_skill or LexUzRAGSkill()
        self.voice_skill = voice_skill or MultimodalVoiceDMSkill()
        self.handoff_skill = handoff_skill or HumanAgentHandoffSkill()
        self.policy_skill = policy_skill or MetaPolicyEnforcerSkill()
        self.conversion_skill = conversion_skill or LeadConversionSkill()

    def verify_webhook(self, mode: str | None, token: str | None, challenge: str | None) -> str | None:
        """Verify Meta Webhook subscription token and return challenge string if valid."""
        if mode == "subscribe" and token == settings.INSTAGRAM_VERIFY_TOKEN:
            logger.info("Meta webhook verified successfully")
            return challenge
        logger.warning("Meta webhook verification failed: mode=%s, token mismatch", mode)
        return None

    async def handle_comment_event(
        self,
        comment_data: dict[str, Any],
        redis_client: Any | None = None,
    ) -> bool:
        """Process an incoming comment from Meta feed webhook."""
        comment_id = str(comment_data.get("id") or comment_data.get("comment_id") or "")
        comment_text = str(comment_data.get("text") or comment_data.get("message") or "")

        if not comment_id or not comment_text:
            return False

        # Skill 1: Comment-to-DM keyword detection
        if not self.comment_skill.matches_comment(comment_text):
            return False

        can_send = await self.comment_skill.can_send_private_reply(comment_id, redis_client)
        if not can_send:
            return False

        payload = self.comment_skill.build_private_reply_payload(comment_id)
        success = await self._send_meta_request(
            endpoint=payload["endpoint"],
            method=payload["method"],
            json_body=payload["body"],
            redis_client=redis_client,
        )

        if success:
            await self.comment_skill.mark_reply_sent(comment_id, redis_client)
            logger.info("Private reply sent for comment %s", comment_id)

        return success

    async def handle_direct_message(
        self,
        sender_id: str,
        message_data: dict[str, Any],
        redis_client: Any | None = None,
        db_session: Any | None = None,
    ) -> list[str]:
        """Process an incoming Instagram Direct Message (text or voice)."""
        start_time = time.time()

        # Skill 7: Check if lawyer manual takeover pause is active
        if redis_client is not None:
            is_paused = await self.handoff_skill.is_ai_paused(sender_id, redis_client)
            if is_paused:
                logger.info("AI is paused for user %s due to lawyer takeover. Skipping", sender_id)
                return []

        # Skill 2: Update 24h inbound activity window
        last_inbound = await self.contact_skill.update_inbound_activity(sender_id, redis_client)

        # Extract text or process audio voice DM
        user_text = message_data.get("text") or ""
        attachments = message_data.get("attachments") or []

        # Skill 6: Multimodal Voice DM processing
        if not user_text and attachments:
            for att in attachments:
                if self.voice_skill.is_voice_attachment(att):
                    audio_url = self.voice_skill.extract_audio_url(att)
                    if audio_url:
                        # In production we download audio, here we check if raw bytes exist or transcribe
                        user_text = await self._download_and_transcribe_audio(audio_url)
                        break

        if not user_text:
            return []

        # Skill 2: Check for phone number in user text
        extracted_phone = self.contact_skill.extract_uz_phone(user_text)
        if extracted_phone and redis_client is not None:
            await redis_client.set(f"ig_user_phone:{sender_id}", extracted_phone, ex=86400 * 30)

        # Skill 3: Intercept personal non-legal questions
        if self.persona_skill.is_personal_question(user_text):
            response_text = self.persona_skill.get_personal_question_response(user_text)
            return await self._dispatch_response_chunks(sender_id, response_text, last_inbound, redis_client, start_time)

        # Skill 9: Check remaining free questions
        remaining = await self.conversion_skill.get_remaining_free_questions(sender_id, redis_client)
        if remaining <= 0:
            upsell_msg = self.conversion_skill.get_exhausted_limit_message()
            return await self._dispatch_response_chunks(sender_id, upsell_msg, last_inbound, redis_client, start_time)

        # Deduct 1 free question
        await self.conversion_skill.decrement_free_question(sender_id, redis_client)

        # Skill 4: Intake & Triage
        _category = self.triage_skill.detect_category(user_text)
        _risk_score, risk_level = self.triage_skill.calculate_risk_score(user_text)
        action_strategy = self.triage_skill.determine_action_strategy(risk_level)

        # If Critical SOS: Return immediate emergency protocol
        if risk_level == RiskLevel.CRITICAL:
            response_text = self.triage_skill.SOS_INSTRUCTIONS
            return await self._dispatch_response_chunks(sender_id, response_text, last_inbound, redis_client, start_time)

        # Skill 5: Lex.uz RAG retrieval
        articles = await self.rag_skill.retrieve_top_articles(user_text, limit=2, db_session=db_session)
        _rag_context = self.rag_skill.build_rag_context_block(articles)

        # Generate response using LLM or curated legal synthesis
        citation = ""
        if articles:
            top_art = articles[0]
            citation = self.rag_skill.format_citation(
                top_art.get("code", "Fuqarolik Kodeksi"),
                top_art.get("article", "modda"),
            )

        response_text = (
            f"Vaziyatingizni ko'rib chiqdim. {citation}, ushbu holatda qonuniy tartib "
            f"va huquqlaringiz himoyasi ta'minlanishi shart.\n\n"
        )

        if action_strategy.get("upsell_type") == "COURT_REPRESENTATION":
            response_text += (
                "Ushbu nizo yuzasidan zudlik bilan sudda vakillik va professional da'vo arizasi "
                "tayyorlash zarur. Sizga individual yordam ko'rsatishimiz uchun bog'lanish "
                "raqamingizni qoldiring."
            )
        elif action_strategy.get("upsell_type") == "CONTRACT_AUDIT":
            response_text += (
                "Keltirilgan holat bo'yicha hujjat va shartnomalarni to'liq huquqiy auditdan "
                "o'tkazishni tavsiya qilaman. Hujjatlaringizni ko'rib chiqishimiz uchun yuborishingiz mumkin."
            )
        else:
            response_text += (
                "Agar sizga qo'shimcha tushuntirish yoki konsultatsiya kerak bo'lsa, "
                "savolingizni batafsil yozib qoldirishingiz mumkin."
            )

        # Skill 3: Sanitize outbound text to guarantee undetectable persona
        clean_text = self.persona_skill.sanitize_outbound_text(response_text)

        # Skill 2: Add phone request if user hasn't provided one yet
        cached_phone = await redis_client.get(f"ig_user_phone:{sender_id}") if redis_client else None
        if not cached_phone and not extracted_phone:
            clean_text += f"\n\n{self.contact_skill.CONTACT_REQUEST_PROMPT}"

        return await self._dispatch_response_chunks(sender_id, clean_text, last_inbound, redis_client, start_time)

    async def _dispatch_response_chunks(
        self,
        recipient_id: str,
        text: str,
        last_inbound_timestamp: float,
        redis_client: Any | None,
        start_time: float,
    ) -> list[str]:
        """Chunk outbound text to 1000 UTF-8 bytes and dispatch with Human Agent tag if needed."""
        # Skill 8: Payload chunking
        chunks = self.policy_skill.split_message_if_exceeds_limit(text)
        current_time = self.contact_skill.get_current_utc_timestamp()

        # Skill 7: Human agent tag check
        use_tag = self.handoff_skill.should_use_human_agent_tag(last_inbound_timestamp, current_time)

        for chunk in chunks:
            # Skill 8: Rate limit slot acquisition
            await self.policy_skill.acquire_rate_limit_slot(redis_client)

            payload = self.handoff_skill.build_outbound_payload(
                recipient_id=recipient_id,
                text=chunk,
                use_human_agent_tag=use_tag,
            )

            await self._send_meta_request(
                endpoint=f"/{settings.INSTAGRAM_GRAPH_API_VERSION}/me/messages",
                method="POST",
                json_body=payload,
                redis_client=redis_client,
            )

        # Skill 8: SLA verification
        self.policy_skill.check_sla_compliance(start_time)
        return chunks

    async def _send_meta_request(
        self,
        endpoint: str,
        method: str = "POST",
        json_body: dict[str, Any] | None = None,
        redis_client: Any | None = None,
    ) -> bool:
        """Send authenticated HTTP request to Meta Graph API."""
        if not settings.INSTAGRAM_ACCESS_TOKEN:
            logger.info("INSTAGRAM_ACCESS_TOKEN not set; skipping live Graph API HTTP request")
            return True

        url = f"https://graph.facebook.com{endpoint}"
        headers = {
            "Authorization": f"Bearer {settings.INSTAGRAM_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.request(method, url, json=json_body, headers=headers)
                return resp.status_code in (200, 201)
        except Exception as e:  # noqa: BLE001
            logger.error("Meta Graph API request error to %s: %s", url, e)
            return False

    async def _download_and_transcribe_audio(self, audio_url: str) -> str:
        """Download audio file from Meta CDN and transcribe."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(audio_url)
                if resp.status_code == 200:
                    return await self.voice_skill.transcribe_audio_bytes(resp.content)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed downloading audio from %s: %s", audio_url, e)
        return ""
