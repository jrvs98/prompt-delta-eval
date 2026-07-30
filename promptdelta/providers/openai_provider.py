from __future__ import annotations

import os
import time
from typing import Any

from .base import Provider, ProviderResponse

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


class OpenAIProvider(Provider):
    def __init__(self, model_name: str, api_key: str | None = None, **kwargs: Any) -> None:
        super().__init__(model_name, **kwargs)
        if OpenAI is None:
            raise ImportError(
                "The 'openai' package isn't installed. Run: pip install openai"
            )
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError(
                "No OpenAI API key found. Set OPENAI_API_KEY in your environment or .env file."
            )
        self._client = OpenAI(api_key=key)

    def complete(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1024) -> ProviderResponse:
        start = time.monotonic()
        try:
            resp = self._client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            text = resp.choices[0].message.content or ""
            latency_ms = int((time.monotonic() - start) * 1000)
            return ProviderResponse(text=text, latency_ms=latency_ms, raw={"id": resp.id})
        except Exception as exc:  # noqa: BLE001 — surface any provider error into the result row
            latency_ms = int((time.monotonic() - start) * 1000)
            return ProviderResponse(text="", latency_ms=latency_ms, error=str(exc))
