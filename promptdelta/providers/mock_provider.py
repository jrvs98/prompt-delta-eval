from __future__ import annotations

import random
import re
import time
from typing import Any

from .base import Provider, ProviderResponse


class MockProvider(Provider):
    """A scripted stand-in for a real model.

    This exists so you can validate the whole pipeline — config loading,
    envelope rendering, provider calls, scoring, storage, and the report —
    with zero API keys and zero cost. It produces plausible-*shaped*
    output (a number where a number is expected, a JSON blob where JSON
    is expected, and so on) but its "correctness" is not meaningful.

    Do not draw conclusions about real models from mock provider results.
    Use it to smoke-test your experiment config before spending API
    credits on the real providers.
    """

    def __init__(self, model_name: str = "mock", seed: int | None = None, **kwargs: Any) -> None:
        super().__init__(model_name, **kwargs)
        seed = seed if seed is not None else (abs(hash(model_name)) % (2**32))
        self.rng = random.Random(seed)

    def complete(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1024) -> ProviderResponse:
        start = time.monotonic()
        condition = self._sniff_condition(prompt)
        text = self._respond(prompt, condition)
        elapsed = int((time.monotonic() - start) * 1000)
        return ProviderResponse(
            text=text,
            latency_ms=elapsed + self.rng.randint(50, 400),
            raw={"mock": True, "condition_guess": condition},
        )

    @staticmethod
    def _sniff_condition(prompt: str) -> str:
        markers_engineered = (
            "step by step",
            "exactly 3 bullet points",
            "valid JSON object",
            "respond with exactly one word",
        )
        if any(m in prompt for m in markers_engineered):
            return "engineered"
        starts_minimal = (
            "solve this",
            "summarize this",
            "classify the sentiment",
            "extract the key fields",
        )
        if prompt.strip().lower().startswith(starts_minimal):
            return "minimal"
        return "bare"

    def _respond(self, prompt: str, condition: str) -> str:
        lower = prompt.lower()
        numbers = re.findall(r"-?\d+\.?\d*", prompt)
        guess = numbers[-1] if numbers else str(self.rng.randint(1, 100))

        if "json object" in lower:
            return '{"name": null, "date": null, "amount": %s}' % (numbers[-1] if numbers else "null")

        if "sentiment" in lower or ("positive" in lower and "negative" in lower):
            label = self.rng.choice(["positive", "negative", "neutral"])
            if condition == "bare":
                return f"I'd say this text comes across as {label} overall, based on the tone."
            return label

        if "bullet" in lower or "summar" in lower:
            n = 3 if condition == "engineered" else self.rng.choice([1, 2, 4])
            if condition == "bare":
                first_sentence = prompt.strip().split(".")[0][:80]
                return f"This text is about {first_sentence}."
            return "\n".join(f"- Mock summary point {i + 1} for pipeline testing." for i in range(n))

        # default: treat as a numeric task
        if condition == "engineered":
            return f"Let's work through this step by step.\n\nAnswer: {guess}"
        return guess
