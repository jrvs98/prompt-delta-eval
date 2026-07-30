from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ProviderResponse:
    text: str
    latency_ms: int
    raw: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class Provider(ABC):
    """Common interface every model backend implements.

    Deliberately narrow: a provider only ever sees a single fully-formed
    prompt string (the envelope has already been applied to the task
    content before it gets here). There is no separate "system prompt"
    concept — for this experiment, using a system prompt at all is
    itself a form of prompt engineering, so the "bare" condition must
    not get one behind the scenes.
    """

    def __init__(self, model_name: str, **kwargs: Any) -> None:
        self.model_name = model_name
        self.extra = kwargs

    @abstractmethod
    def complete(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> ProviderResponse:
        raise NotImplementedError

    def label(self) -> str:
        return f"{self.__class__.__name__}:{self.model_name}"
