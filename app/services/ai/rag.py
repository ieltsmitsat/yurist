"""RAG (Retrieval-Augmented Generation) service for Lex.uz legal knowledge base."""

import logging
from typing import Any

from google import genai
from google.genai import types
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.legal_chunk import LegalChunk

logger = logging.getLogger(__name__)


class RAGService:
    """Manages legal knowledge retrieval from pgvector with SQLite fallback."""

    def __init__(self, client: Any | None = None) -> None:
        if client is not None:
            self.client = client
        else:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def get_embedding(self, text: str) -> list[float]:
        """Compute 1536-dim embedding vector using Gemini or fallback."""
        try:
            # Check Gemini client first
            if hasattr(self.client, "aio") and hasattr(self.client.aio, "models"):
                res = await self.client.aio.models.embed_content(
                    model=settings.GEMINI_EMBEDDING_MODEL,
                    contents=text,
                    config=types.EmbedContentConfig(output_dimensionality=1536),
                )
                if hasattr(res, "embeddings") and res.embeddings:
                    return [float(x) for x in res.embeddings[0].values]
                return []

            # OpenAI client compatibility fallback
            if hasattr(self.client, "embeddings") and hasattr(self.client.embeddings, "create"):
                response = await self.client.embeddings.create(
                    model=settings.EMBEDDING_MODEL,
                    input=text,
                )
                return list(response.data[0].embedding)

            return []
        except Exception as e:
            logger.error("Failed to generate embedding: %s", e)
            raise

    async def search_relevant_laws(
        self,
        query: str,
        session: AsyncSession,
        limit: int = 3,
    ) -> str:
        """Search top-K relevant legal articles in vector store or SQLite keywords."""
        try:
            bind = session.bind
            dialect_name = bind.dialect.name if bind else "sqlite"

            if dialect_name == "sqlite":
                # Keyword matching for local SQLite dev
                words = [w.strip() for w in query.split() if len(w) > 3][:4]
                if words:
                    conditions = [LegalChunk.chunk_text.ilike(f"%{w}%") for w in words]
                    conditions.extend([LegalChunk.law_title.ilike(f"%{w}%") for w in words])
                    stmt = select(LegalChunk).where(or_(*conditions)).limit(limit)
                else:
                    stmt = select(LegalChunk).limit(limit)
            else:
                query_embedding = await self.get_embedding(query)
                if not query_embedding:
                    return ""
                stmt = (
                    select(LegalChunk)
                    .order_by(LegalChunk.embedding.cosine_distance(query_embedding))
                    .limit(limit)
                )

            result = await session.execute(stmt)
            chunks = result.scalars().all()

            if not chunks:
                return ""

            formatted_sections = []
            for chunk in chunks:
                art = f" ({chunk.article_number})" if chunk.article_number else ""
                url = f" [Lex.uz: {chunk.lex_url}]" if chunk.lex_url else ""
                formatted_sections.append(f"📖 {chunk.law_title}{art}{url}:\n{chunk.chunk_text}")

            return "\n\n".join(formatted_sections)
        except Exception as e:  # noqa: BLE001
            logger.warning("RAG vector search warning (falling back gracefully): %s", e)
            return ""
