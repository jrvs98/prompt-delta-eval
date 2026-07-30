from __future__ import annotations

import os
import time
from typing import Any

from .base import Provider, ProviderResponse

try:
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None


class AnthropicProvider(Provider):
    def __init__(self, model_name: str, api_key: str | None = None, **kwargs: Any) -> None:
        super().__init__(model_name, **kwargs)
        if anthropic is None:
            raise ImportError(
                "The 'anthropic' package isn't installed. Run: pip install anthropic"
            )
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError(
                "No Anthropic API key found. Set ANTHROPIC_API_KEY in your environment or .env file."
            )
        self._client = anthropic.Anthropic(api_key=key)

    def complete(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1024) -> ProviderResponse:
        start = time.monotonic()
        try:
            resp = self._client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
            latency_ms = int((time.monotonic() - start) * 1000)
            return ProviderResponse(text=text, latency_ms=latency_ms, raw={"id": resp.id})
        except Exception as exc:  # noqa: BLE001
            latency_ms = int((time.monotonic() - start) * 1000)
            return ProviderResponse(text="", latency_ms=latency_ms, error=str(exc))
