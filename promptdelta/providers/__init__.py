from __future__ import annotations

from typing import Any, Dict, Type

from .base import Provider, ProviderResponse
from .mock_provider import MockProvider

_REGISTRY: Dict[str, Type[Provider]] = {
    "mock": MockProvider,
}


def _lazy_register() -> None:
    """Providers with heavy/optional SDK imports are registered lazily so
    that `import promptdelta` never fails just because you haven't
    installed every provider's SDK."""
    if "openai" not in _REGISTRY:
        from .openai_provider import OpenAIProvider

        _REGISTRY["openai"] = OpenAIProvider
    if "anthropic" not in _REGISTRY:
        from .anthropic_provider import AnthropicProvider

        _REGISTRY["anthropic"] = AnthropicProvider
    if "google" not in _REGISTRY:
        from .google_provider import GoogleProvider

        _REGISTRY["google"] = GoogleProvider
    if "ollama" not in _REGISTRY:
        from .ollama_provider import OllamaProvider

        _REGISTRY["ollama"] = OllamaProvider


def get_provider(provider_name: str, model_name: str, **kwargs: Any) -> Provider:
    _lazy_register()
    try:
        cls = _REGISTRY[provider_name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown provider '{provider_name}'. Available: {sorted(_REGISTRY)}"
        ) from exc
    return cls(model_name, **kwargs)


__all__ = ["Provider", "ProviderResponse", "get_provider", "MockProvider"]
