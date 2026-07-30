from __future__ import annotations

import os
import time
from typing import Any

from .base import Provider, ProviderResponse

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover
    genai = None


class GoogleProvider(Provider):
    def __init__(self, model_name: str, api_key: str | None = None, **kwargs: Any) -> None:
        super().__init__(model_name, **kwargs)
        if genai is None:
            raise ImportError(
                "The 'google-generativeai' package isn't installed. "
                "Run: pip install google-generativeai"
            )
        key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ValueError(
                "No Google API key found. Set GOOGLE_API_KEY in your environment or .env file."
            )
        genai.configure(api_key=key)
        self._model = genai.GenerativeModel(model_name)

    def complete(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1024) -> ProviderResponse:
        start = time.monotonic()
        try:
            resp = self._model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                },
            )
            text = resp.text or ""
            latency_ms = int((time.monotonic() - start) * 1000)
            return ProviderResponse(text=text, latency_ms=latency_ms, raw={})
        except Exception as exc:  # noqa: BLE001
            latency_ms = int((time.monotonic() - start) * 1000)
            return ProviderResponse(text="", latency_ms=latency_ms, error=str(exc))
