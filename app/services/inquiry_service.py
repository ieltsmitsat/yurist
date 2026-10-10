"""Inquiry processing service (Text, Voice, Document Express Audits)."""

import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.attachment import Attachment
from app.db.models.inquiry import Inquiry
from app.db.models.user import User
from app.services.ai.document import DocumentParser
from app.services.ai.llm_client import LegalAnalysisResult, LLMService
from app.services.ai.rag import RAGService
from app.services.ai.speech import SpeechService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


class InquiryService:
    """Orchestrates legal inquiries, express audits, and multimodal processing."""

    def __init__(
        self,
        llm_service: LLMService | None = None,
        rag_service: RAGService | None = None,
        speech_service: SpeechService | None = None,
    ) -> None:
        self.llm = llm_service or LLMService()
        self.rag = rag_service or RAGService()
        self.speech = speech_service or SpeechService()

    async def process_text_inquiry(
        self,
        session: AsyncSession,
        user: User,
        question_text: str,
    ) -> tuple[Inquiry, LegalAnalysisResult]:
        """Process a text inquiry from the user."""
        # Retrieve relevant legal context from pgvector RAG
        rag_context = await self.rag.search_relevant_laws(question_text, session=session, limit=3)

        # Generate legal response with Undetectable AI Persona
        analysis = await self.llm.analyze_legal_inquiry(
            question=question_text,
            language=user.language,
            rag_context=rag_context,
        )

        # Decrement free question credit only for genuine legal inquiries
        if analysis.is_legal_case:
            await UserService.decrement_question(session, user)

        inquiry = Inquiry(
            user_id=user.id,
            question_text=question_text,
            risk_level=analysis.risk_level,
            risk_score=analysis.risk_score,
            ai_draft_response=analysis.response_text,
            ai_upsell_offer=analysis.upsell_offer,
            final_response=analysis.response_text,
            status="answered",
            answered_at=datetime.now(UTC),
        )
        session.add(inquiry)
        await session.commit()
        await session.refresh(inquiry)

        logger.info(
            "Processed text inquiry #%d for user #%d: risk=%s (%d/100)",
            inquiry.id,
            user.id,
            inquiry.risk_level,
            inquiry.risk_score or 0,
        )
        return inquiry, analysis

    async def process_voice_inquiry(
        self,
        session: AsyncSession,
        user: User,
        audio_path: str | Path,
    ) -> tuple[Inquiry, LegalAnalysisResult]:
        """Transcribe voice memo via Whisper and process as legal inquiry."""
        transcript = await self.speech.transcribe_audio(audio_path, language=user.language)

        inquiry, analysis = await self.process_text_inquiry(session, user, transcript)
        inquiry.stt_transcript = transcript
        await session.commit()
        await session.refresh(inquiry)
        return inquiry, analysis

    async def process_express_audit(
        self,
        session: AsyncSession,
        user: User,
        filename: str,
        file_bytes: bytes,
    ) -> tuple[Inquiry, LegalAnalysisResult]:
        """Run express legal audit on an uploaded document (.pdf, .docx)."""
        # Extract text from document
        extracted_text = DocumentParser.extract_text(filename, file_bytes)

        # Run express audit analysis
        analysis = await self.llm.analyze_express_audit(
            document_text=extracted_text,
            language=user.language,
        )

        # Decrement question credit after successful audit
        await UserService.decrement_question(session, user)

        inquiry = Inquiry(
            user_id=user.id,
            question_text=f"Express audit: {filename}",
            risk_level=analysis.risk_level,
            risk_score=analysis.risk_score,
            ai_draft_response=analysis.response_text,
            ai_upsell_offer=analysis.upsell_offer,
            final_response=analysis.response_text,
            status="answered",
            answered_at=datetime.now(UTC),
        )
        session.add(inquiry)
        await session.flush()

        # Save attachment record
        attachment = Attachment(
            inquiry_id=inquiry.id,
            file_type=filename.lower().rsplit(".", 1)[-1],
            file_url=f"local://uploads/{filename}",
            extracted_text=extracted_text[:10000],  # store first 10k chars
        )
        session.add(attachment)
        await session.commit()
        await session.refresh(inquiry)

        logger.info(
            "Completed express audit for document %s, user #%d: risk_score=%d",
            filename,
            user.id,
            analysis.risk_score,
        )
        return inquiry, analysis
