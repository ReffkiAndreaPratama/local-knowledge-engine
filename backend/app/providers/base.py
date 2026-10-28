"""Provider interface and shared types."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderError(RuntimeError):
    """Raised when an AI provider cannot produce an answer."""


@dataclass
class ProviderInfo:
    name: str
    model: str
    is_local: bool
    configured: bool


class AIProvider(ABC):
    """Minimal text-completion interface."""

    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        """Whether the provider has everything it needs to run."""

    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Return the model's answer text."""

    def info(self, model: str) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            model=model,
            is_local=self.name == "ollama",
            configured=self.is_configured(),
        )
