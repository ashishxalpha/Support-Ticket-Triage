"""
Abstract AI provider interface.

All LLM providers (OpenAI, Anthropic, Ollama) implement this interface,
enabling provider-agnostic AI operations throughout the application.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClassificationResult:
    """Result from ticket classification."""

    category: str
    confidence: float
    reasoning: str = ""


@dataclass
class PriorityResult:
    """Result from priority prediction."""

    priority: str
    confidence: float
    reasoning: str = ""
    sentiment_score: float = 0.0
    sentiment_label: str = "neutral"


@dataclass
class SummaryResult:
    """Result from ticket summarization."""

    summary: str
    key_points: list[str] = field(default_factory=list)


@dataclass
class ResponseResult:
    """Result from AI response generation."""

    response: str
    confidence: float = 0.0
    sources_used: int = 0


@dataclass
class EmbeddingResult:
    """Result from text embedding."""

    embedding: list[float]
    model: str
    token_count: int = 0


class AIProvider(ABC):
    """Abstract interface for AI/LLM providers."""

    @abstractmethod
    async def classify_ticket(
        self, title: str, description: str
    ) -> ClassificationResult:
        """Classify a ticket into a category."""
        ...

    @abstractmethod
    async def predict_priority(
        self,
        title: str,
        description: str,
        category: str,
        customer_tier: str = "standard",
    ) -> PriorityResult:
        """Predict ticket priority/severity."""
        ...

    @abstractmethod
    async def summarize_ticket(
        self, title: str, description: str
    ) -> SummaryResult:
        """Generate a concise ticket summary for agents."""
        ...

    @abstractmethod
    async def generate_response(
        self,
        title: str,
        description: str,
        category: str,
        priority: str,
        similar_tickets: str | None = None,
    ) -> ResponseResult:
        """Generate a draft response for the support ticket."""
        ...

    @abstractmethod
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """Generate a vector embedding for the given text."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the AI provider is accessible."""
        ...
