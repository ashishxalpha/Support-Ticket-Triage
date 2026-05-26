"""
AI Triage Service — orchestrates the full AI triage pipeline.

This is the core intelligence layer that processes tickets through:
classification → priority prediction → summarization → response generation → embedding → routing
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProvider
from app.ai.factory import get_ai_provider
from app.core.logging import get_logger
from app.models.ticket import TicketCategory, TicketPriority
from app.repositories.team import TeamRepository
from app.repositories.ticket import TicketRepository
from app.services.rag_service import RAGService

logger = get_logger("ai_triage")


class AITriageService:
    """Orchestrates the complete AI triage pipeline for support tickets."""

    def __init__(self, db: AsyncSession, provider: AIProvider | None = None) -> None:
        self.db = db
        self.provider = provider or get_ai_provider()
        self.ticket_repo = TicketRepository(db)
        self.team_repo = TeamRepository(db)

    async def triage_ticket(self, ticket_id: uuid.UUID) -> dict[str, Any]:
        """
        Execute the full triage pipeline on a ticket.

        Steps:
        1. Classify category
        2. Predict priority
        3. Generate summary
        4. Generate embedding
        5. Find similar tickets
        6. Generate AI response (using RAG context)
        7. Route to appropriate team
        8. Update ticket with all AI results
        """
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if not ticket:
            logger.error("Ticket not found for triage", ticket_id=str(ticket_id))
            return {"error": "Ticket not found"}

        logger.info(
            "Starting triage pipeline",
            ticket_id=str(ticket_id),
            ticket_number=ticket.ticket_number,
        )

        results: dict[str, Any] = {}
        customer_tier = "standard"
        if ticket.customer_user:
            customer_tier = ticket.customer_user.customer_tier or "standard"

        # Step 1: Classification
        try:
            classification = await self.provider.classify_ticket(
                title=ticket.title,
                description=ticket.description,
            )
            results["classification"] = {
                "category": classification.category,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning,
            }
            logger.info(
                "Classification complete",
                ticket_id=str(ticket_id),
                category=classification.category,
                confidence=classification.confidence,
            )
        except Exception as e:
            logger.error("Classification failed", ticket_id=str(ticket_id), error=str(e))
            classification = None

        # Step 2: Priority prediction
        try:
            category_str = classification.category if classification else "general_inquiry"
            priority_result = await self.provider.predict_priority(
                title=ticket.title,
                description=ticket.description,
                category=category_str,
                customer_tier=customer_tier,
            )
            results["priority"] = {
                "priority": priority_result.priority,
                "confidence": priority_result.confidence,
                "sentiment_score": priority_result.sentiment_score,
                "sentiment_label": priority_result.sentiment_label,
            }
            logger.info(
                "Priority prediction complete",
                ticket_id=str(ticket_id),
                priority=priority_result.priority,
                sentiment=priority_result.sentiment_label,
            )
        except Exception as e:
            logger.error("Priority prediction failed", ticket_id=str(ticket_id), error=str(e))
            priority_result = None

        # Step 3: Summary
        try:
            summary_result = await self.provider.summarize_ticket(
                title=ticket.title,
                description=ticket.description,
            )
            results["summary"] = summary_result.summary
        except Exception as e:
            logger.error("Summarization failed", ticket_id=str(ticket_id), error=str(e))
            summary_result = None

        # Step 4: Generate embedding
        embedding_data = None
        try:
            embed_text = f"{ticket.title}\n\n{ticket.description}"
            embedding_result = await self.provider.generate_embedding(embed_text)
            embedding_data = embedding_result.embedding
            await self.ticket_repo.update_embedding(ticket_id, embedding_data)
            logger.info("Embedding generated", ticket_id=str(ticket_id))
        except Exception as e:
            logger.error("Embedding generation failed", ticket_id=str(ticket_id), error=str(e))

        # Step 5: Find similar tickets and KB articles (RAG retrieval)
        rag_context_str = None
        if embedding_data:
            try:
                rag_service = RAGService(self.db, self.provider)
                # Since we already have the embedding, we could pass it, but RAGService currently takes a query string.
                # The task is to get context, so we'll pass the ticket text.
                query_text = f"{ticket.title}\n\n{ticket.description}"
                contexts = await rag_service.retrieve_context(
                    query=query_text,
                    limit=5,
                    threshold=0.70,
                    exclude_ticket_id=ticket_id,
                )
                
                rag_context_str = rag_service.format_context_for_prompt(contexts)
                results["rag_sources"] = len(contexts)
                
                logger.info(
                    "RAG context retrieved",
                    ticket_id=str(ticket_id),
                    count=len(contexts),
                )
            except Exception as e:
                logger.error(
                    "RAG retrieval failed",
                    ticket_id=str(ticket_id),
                    error=str(e),
                )

        # Step 6: Generate AI response (with RAG context)
        try:
            category_str = classification.category if classification else "general_inquiry"
            priority_str = priority_result.priority if priority_result else "medium"
            response_result = await self.provider.generate_response(
                title=ticket.title,
                description=ticket.description,
                category=category_str,
                priority=priority_str,
                similar_tickets=rag_context_str,
            )
            results["ai_response"] = response_result.response[:500]
        except Exception as e:
            logger.error("Response generation failed", ticket_id=str(ticket_id), error=str(e))
            response_result = None

        # Step 7: Route to team
        team_id = None
        if classification:
            try:
                team = await self.team_repo.get_team_for_category(classification.category)
                if team:
                    team_id = team.id
                    results["routed_team"] = team.name
                    logger.info(
                        "Ticket routed",
                        ticket_id=str(ticket_id),
                        team=team.name,
                    )
            except Exception as e:
                logger.error("Routing failed", ticket_id=str(ticket_id), error=str(e))

        # Step 8: Update ticket with all AI results
        update_data: dict[str, Any] = {"is_triaged": True}

        if classification:
            update_data["predicted_category"] = TicketCategory(classification.category)
            update_data["category_confidence"] = classification.confidence
            # Auto-set category if not manually set
            if not ticket.category:
                update_data["category"] = TicketCategory(classification.category)

        if priority_result:
            update_data["predicted_priority"] = TicketPriority(priority_result.priority)
            update_data["priority_confidence"] = priority_result.confidence
            update_data["sentiment_score"] = priority_result.sentiment_score
            update_data["sentiment_label"] = priority_result.sentiment_label
            # Auto-set priority if still default
            if ticket.priority == TicketPriority.MEDIUM:
                update_data["priority"] = TicketPriority(priority_result.priority)

        if summary_result:
            update_data["ai_summary"] = summary_result.summary

        if response_result:
            update_data["ai_response"] = response_result.response
            update_data["ai_confidence"] = response_result.confidence

        if team_id:
            update_data["assigned_team_id"] = team_id

        await self.ticket_repo.update(ticket_id, **update_data)

        logger.info(
            "Triage pipeline complete",
            ticket_id=str(ticket_id),
            results=results,
        )

        return results
