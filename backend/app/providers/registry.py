"""Provider registry."""
from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.providers.base import AIProvider, ProviderError, ProviderInfo
from app.providers.ollama import OllamaProvider
from app.providers.openai_compat import OpenAICompatibleProvider


def get_provider(name: Optional[str] = None) -> AIProvider:
    """Resolve a provider by name, defaulting to the configured one."""
    resolved = (name or settings.AI_PROVIDER or "").lower()
    if resolved == "ollama":
        return OllamaProvider()
    if resolved in {"openai", "openai-compatible", "lmstudio", "vllm"}:
        return OpenAICompatibleProvider()
    raise ProviderError(f"Unknown AI provider: {resolved}")


def get_provider_info() -> ProviderInfo:
    try:
        provider = get_provider()
        return provider.info(getattr(provider, "model", settings.AI_MODEL))
    except ProviderError:
        return ProviderInfo(
            name=settings.AI_PROVIDER,
            model=settings.AI_MODEL,
            is_local=settings.AI_PROVIDER == "ollama",
            configured=False,
        )


__all__ = [
    "AIProvider",
    "ProviderError",
    "ProviderInfo",
    "get_provider",
    "get_provider_info",
]
