"""
Anthropic provider — placeholder implementation.

Provides the same interface as OpenAI but is not yet connected to a real API.
This allows seamless switching once Anthropic integration is needed.
"""

from __future__ import annotations

from typing import Any

from app.ai.base import (
    AIProvider,
    ClassificationResult,
    EmbeddingResult,
    PriorityResult,
    ResponseResult,
    SummaryResult,
)
from app.core.logging import get_logger

logger = get_logger("anthropic_provider")


class AnthropicProvider(AIProvider):
    """Placeholder Anthropic provider — returns sensible defaults."""

    async def classify_ticket(
        self, title: str, description: str
    ) -> ClassificationResult:
        logger.warning("Anthropic provider not implemented — returning default classification")
        return ClassificationResult(
            category="general_inquiry",
            confidence=0.0,
            reasoning="Anthropic provider not yet implemented",
        )

    async def predict_priority(
        self,
        title: str,
        description: str,
        category: str,
        customer_tier: str = "standard",
    ) -> PriorityResult:
        logger.warning("Anthropic provider not implemented — returning default priority")
        return PriorityResult(
            priority="medium",
            confidence=0.0,
            reasoning="Anthropic provider not yet implemented",
        )

    async def summarize_ticket(
        self, title: str, description: str
    ) -> SummaryResult:
        return SummaryResult(summary="Summary unavailable — Anthropic provider not implemented")

    async def generate_response(
        self,
        title: str,
        description: str,
        category: str,
        priority: str,
        similar_tickets: list[dict[str, Any]] | None = None,
    ) -> ResponseResult:
        return ResponseResult(response="", confidence=0.0)

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        # Return zero vector as placeholder
        return EmbeddingResult(
            embedding=[0.0] * 1536,
            model="anthropic-placeholder",
        )

    async def health_check(self) -> bool:
        return False
