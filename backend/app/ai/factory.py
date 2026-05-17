"""
AI provider factory — creates the appropriate provider based on configuration.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.base import AIProvider
from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    """Create and cache the configured AI provider instance."""
    settings = get_settings()

    match settings.ai_provider:
        case "openai":
            from app.ai.openai_provider import OpenAIProvider
            return OpenAIProvider()
        case "anthropic":
            from app.ai.anthropic_provider import AnthropicProvider
            return AnthropicProvider()
        case "ollama":
            # Ollama support can be added by implementing AIProvider
            from app.ai.anthropic_provider import AnthropicProvider
            return AnthropicProvider()
        case _:
            from app.ai.openai_provider import OpenAIProvider
            return OpenAIProvider()
