"""
RAG Service — Orchestrates hybrid retrieval across multiple knowledge indexes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProvider
from app.repositories.knowledge_base import KnowledgeBaseRepository
from app.repositories.ticket import TicketRepository
from app.core.logging import get_logger

logger = get_logger("rag_service")


@dataclass
class RetrievedContext:
    """Standardized retrieved context from various sources."""
    id: uuid.UUID
    source_type: str  # "knowledge_base", "ticket", "comment"
    title: str
    content: str
    score: float
    url: str | None = None
    metadata: dict[str, Any] | None = None


class RAGService:
    """Service for Retrieval Augmented Generation operations."""

    def __init__(self, db: AsyncSession, ai_provider: AIProvider):
        self.db = db
        self.ai = ai_provider
        self.kb_repo = KnowledgeBaseRepository(db)
        self.ticket_repo = TicketRepository(db)

    async def retrieve_context(
        self,
        query: str,
        limit: int = 5,
        threshold: float = 0.65,
        exclude_ticket_id: uuid.UUID | None = None,
    ) -> list[RetrievedContext]:
        """
        Retrieve multi-modal context (KB + Tickets) for a given query.
        Uses vector search and weights results.
        """
        # 1. Generate embedding for query
        try:
            embedding_result = await self.ai.generate_embedding(query)
            query_vector = embedding_result.embedding
        except Exception as e:
            logger.error("Failed to generate embedding for RAG query", error=str(e))
            return []

        # 2. Retrieve from Knowledge Base
        kb_results = await self.kb_repo.find_similar(
            embedding=query_vector,
            limit=limit,
            threshold=threshold,
        )

        # 3. Retrieve from Historical Tickets
        ticket_results = await self.ticket_repo.find_similar(
            embedding=query_vector,
            limit=limit,
            threshold=threshold,
            exclude_id=exclude_ticket_id,
        )

        # 4. Normalize and combine results
        contexts: list[RetrievedContext] = []

        # We give a slight boost to KB articles as they are canonical knowledge
        for article, score in kb_results:
            contexts.append(
                RetrievedContext(
                    id=article.id,
                    source_type="knowledge_base",
                    title=article.title,
                    content=article.content,
                    score=score * 1.1,  # 10% boost to KB
                    metadata={"category": article.category},
                )
            )

        for ticket, score in ticket_results:
            # Only use resolved or closed tickets as good context
            if ticket.status.value not in ("resolved", "closed"):
                # Penalize open tickets
                score = score * 0.8

            contexts.append(
                RetrievedContext(
                    id=ticket.id,
                    source_type="ticket",
                    title=ticket.title,
                    content=ticket.description,
                    score=score,
                    metadata={
                        "status": ticket.status.value,
                        "category": ticket.category.value if ticket.category else None,
                        "resolution": ticket.ai_response or "See comments for resolution.",
                    },
                )
            )

        # 5. Sort by combined score and limit
        contexts.sort(key=lambda x: x.score, reverse=True)
        return contexts[:limit]

    def format_context_for_prompt(self, contexts: list[RetrievedContext]) -> str:
        """Format retrieved contexts into a string suitable for LLM injection."""
        if not contexts:
            return "No relevant past context found."

        formatted_sections = []
        
        kb_contexts = [c for c in contexts if c.source_type == "knowledge_base"]
        ticket_contexts = [c for c in contexts if c.source_type == "ticket"]

        if kb_contexts:
            formatted_sections.append("### RELEVANT KNOWLEDGE BASE ARTICLES ###")
            for i, ctx in enumerate(kb_contexts, 1):
                formatted_sections.append(f"Article {i}: {ctx.title}")
                formatted_sections.append(f"Content: {ctx.content}")
                formatted_sections.append("---")

        if ticket_contexts:
            formatted_sections.append("### RELEVANT HISTORICAL TICKETS ###")
            for i, ctx in enumerate(ticket_contexts, 1):
                formatted_sections.append(f"Ticket {i}: {ctx.title}")
                formatted_sections.append(f"Issue: {ctx.content}")
                if ctx.metadata and "resolution" in ctx.metadata:
                    formatted_sections.append(f"Resolution/Response: {ctx.metadata['resolution']}")
                formatted_sections.append("---")

        return "\n".join(formatted_sections)
