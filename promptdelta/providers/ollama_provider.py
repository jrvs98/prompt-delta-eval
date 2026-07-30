from __future__ import annotations

import os
import time
from typing import Any

import requests

from .base import Provider, ProviderResponse


class OllamaProvider(Provider):
    """Talks to a local Ollama server (https://ollama.com). No API key
    needed — just make sure `ollama serve` is running and the model has
    been pulled (`ollama pull <model_name>`).
    """

    def __init__(self, model_name: str, host: str | None = None, **kwargs: Any) -> None:
        super().__init__(model_name, **kwargs)
        self.host = (host or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")

    def complete(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1024) -> ProviderResponse:
        start = time.monotonic()
        try:
            resp = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data.get("response", "")
            latency_ms = int((time.monotonic() - start) * 1000)
            return ProviderResponse(text=text, latency_ms=latency_ms, raw={})
        except Exception as exc:  # noqa: BLE001
            latency_ms = int((time.monotonic() - start) * 1000)
            return ProviderResponse(
                text="",
                latency_ms=latency_ms,
                error=f"{exc} (is `ollama serve` running and is '{self.model_name}' pulled?)",
            )
