from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

VALID_CONDITIONS = ("bare", "minimal", "engineered")


class EnvelopeBook:
    """Loads envelope templates from YAML and renders them for a given
    task type + condition + item.
    """

    def __init__(self, path: str | Path):
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self.task_types: Dict[str, Dict[str, str]] = data.get("task_types", {})
        if not self.task_types:
            raise ValueError(f"No task_types found in envelope file: {path}")

    def render(self, task_type: str, condition: str, content: str, extra_fields: Dict[str, Any] | None = None) -> str:
        if condition not in VALID_CONDITIONS:
            raise ValueError(f"Unknown condition '{condition}'. Must be one of {VALID_CONDITIONS}.")
        if task_type not in self.task_types:
            raise ValueError(
                f"No envelope templates defined for task type '{task_type}'. "
                f"Available: {sorted(self.task_types)}"
            )
        templates = self.task_types[task_type]
        if condition not in templates:
            raise ValueError(f"Task type '{task_type}' has no '{condition}' template defined.")
        template = templates[condition]
        fields = {"content": content, **(extra_fields or {})}
        try:
            return template.format(**fields)
        except KeyError as exc:
            raise ValueError(
                f"Envelope template for task type '{task_type}' / condition '{condition}' "
                f"references a placeholder {exc} that wasn't supplied. "
                f"If it's a task-specific field (like {{schema_hint}}), add it under that "
                f"task's YAML file."
            ) from exc
