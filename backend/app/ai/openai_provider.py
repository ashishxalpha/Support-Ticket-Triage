"""
OpenAI provider implementation.

Implements all AI operations using OpenAI's GPT and embedding models
with structured JSON output, retry logic, and error handling.
"""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI, APIError, RateLimitError

from app.ai.base import (
    AIProvider,
    ClassificationResult,
    EmbeddingResult,
    PriorityResult,
    ResponseResult,
    SummaryResult,
)
from app.ai.prompts import (
    PRIORITY_PREDICTION_PROMPT,
    RESPONSE_GENERATION_PROMPT,
    SIMILAR_CONTEXT_TEMPLATE,
    SIMILAR_TICKET_TEMPLATE,
    TICKET_CLASSIFICATION_PROMPT,
    TICKET_SUMMARY_PROMPT,
)
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("openai_provider")
settings = get_settings()


class OpenAIProvider(AIProvider):
    """OpenAI-based AI provider for ticket triage operations."""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.embedding_model = settings.openai_embedding_model
        self.max_tokens = settings.openai_max_tokens
        self.temperature = settings.openai_temperature

    async def _chat_completion(self, prompt: str, max_retries: int = 3) -> str:
        """Execute a chat completion with retry logic."""
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a precise AI assistant. Always respond with valid JSON only.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content
                if content:
                    return content.strip()
                raise ValueError("Empty response from OpenAI")
            except RateLimitError:
                if attempt < max_retries - 1:
                    import asyncio
                    wait_time = 2 ** (attempt + 1)
                    logger.warning(
                        "OpenAI rate limit hit, retrying",
                        attempt=attempt + 1,
                        wait_seconds=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise
            except APIError as e:
                logger.error("OpenAI API error", error=str(e), attempt=attempt + 1)
                if attempt == max_retries - 1:
                    raise
        raise RuntimeError("Max retries exceeded")

    def _parse_json(self, text: str) -> dict[str, Any]:
        """Parse JSON from LLM response, handling common formatting issues."""
        # Strip markdown code blocks if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])
        return json.loads(cleaned)

    async def classify_ticket(
        self, title: str, description: str
    ) -> ClassificationResult:
        prompt = TICKET_CLASSIFICATION_PROMPT.format(title=title, description=description)
        raw = await self._chat_completion(prompt)
        data = self._parse_json(raw)

        valid_categories = [
            "billing", "technical", "bug", "feature_request",
            "security", "account", "refund", "general_inquiry",
        ]
        category = data.get("category", "general_inquiry").lower()
        if category not in valid_categories:
            category = "general_inquiry"

        return ClassificationResult(
            category=category,
            confidence=min(max(float(data.get("confidence", 0.5)), 0.0), 1.0),
            reasoning=data.get("reasoning", ""),
        )

    async def predict_priority(
        self,
        title: str,
        description: str,
        category: str,
        customer_tier: str = "standard",
    ) -> PriorityResult:
        prompt = PRIORITY_PREDICTION_PROMPT.format(
            title=title,
            description=description,
            category=category,
            customer_tier=customer_tier,
        )
        raw = await self._chat_completion(prompt)
        data = self._parse_json(raw)

        valid_priorities = ["low", "medium", "high", "critical"]
        priority = data.get("priority", "medium").lower()
        if priority not in valid_priorities:
            priority = "medium"

        return PriorityResult(
            priority=priority,
            confidence=min(max(float(data.get("confidence", 0.5)), 0.0), 1.0),
            reasoning=data.get("reasoning", ""),
            sentiment_score=min(max(float(data.get("sentiment_score", 0.0)), -1.0), 1.0),
            sentiment_label=data.get("sentiment_label", "neutral"),
        )

    async def summarize_ticket(
        self, title: str, description: str
    ) -> SummaryResult:
        prompt = TICKET_SUMMARY_PROMPT.format(title=title, description=description)
        raw = await self._chat_completion(prompt)
        data = self._parse_json(raw)

        return SummaryResult(
            summary=data.get("summary", ""),
            key_points=data.get("key_points", []),
        )

    async def generate_response(
        self,
        title: str,
        description: str,
        category: str,
        priority: str,
        similar_tickets: list[dict[str, Any]] | None = None,
    ) -> ResponseResult:
        # Build similar tickets context
        similar_context = ""
        if similar_tickets:
            ticket_strs = []
            for t in similar_tickets[:3]:
                ticket_strs.append(
                    SIMILAR_TICKET_TEMPLATE.format(
                        title=t.get("title", ""),
                        category=t.get("category", ""),
                        resolution=t.get("resolution", "No resolution recorded"),
                        similarity=round(t.get("similarity", 0) * 100),
                    )
                )
            similar_context = SIMILAR_CONTEXT_TEMPLATE.format(
                tickets="\n".join(ticket_strs)
            )

        prompt = RESPONSE_GENERATION_PROMPT.format(
            title=title,
            description=description,
            category=category,
            priority=priority,
            similar_context=similar_context,
        )
        raw = await self._chat_completion(prompt)
        data = self._parse_json(raw)

        return ResponseResult(
            response=data.get("response", ""),
            confidence=min(max(float(data.get("confidence", 0.5)), 0.0), 1.0),
            sources_used=int(data.get("sources_used", 0)),
        )

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        # Truncate text to avoid token limits
        truncated = text[:8000]

        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=truncated,
        )

        return EmbeddingResult(
            embedding=response.data[0].embedding,
            model=self.embedding_model,
            token_count=response.usage.total_tokens if response.usage else 0,
        )

    async def health_check(self) -> bool:
        try:
            response = await self.client.models.list()
            return True
        except Exception as e:
            logger.error("OpenAI health check failed", error=str(e))
            return False
