from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class TaskItem:
    id: str
    content: str
    expected: Any = None


@dataclass
class EvalSpec:
    method: str  # exact_match | numeric_tolerance | regex | json_schema | llm_judge
    tolerance: float = 0.0
    normalize: bool = True
    required_keys: List[str] = field(default_factory=list)
    rubric: str = ""


@dataclass
class FormatSpec:
    rule: str = "none"  # none | one_word | bullet_count | json | word_limit
    count: Optional[int] = None
    limit: Optional[int] = None


@dataclass
class Task:
    id: str
    type: str
    description: str
    eval: EvalSpec
    format: FormatSpec
    items: List[TaskItem]
    extra_fields: Dict[str, Any] = field(default_factory=dict)  # e.g. schema_hint for extraction


def load_task(path: str | Path) -> Task:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    required_top = ("id", "type", "eval", "items")
    missing = [k for k in required_top if k not in data]
    if missing:
        raise ValueError(f"Task file {path} is missing required field(s): {missing}")

    eval_data = data["eval"]
    eval_spec = EvalSpec(
        method=eval_data["method"],
        tolerance=eval_data.get("tolerance", 0.0),
        normalize=eval_data.get("normalize", True),
        required_keys=eval_data.get("required_keys", []),
        rubric=eval_data.get("rubric", ""),
    )

    format_data = data.get("format", {}) or {}
    format_spec = FormatSpec(
        rule=format_data.get("rule", "none"),
        count=format_data.get("count"),
        limit=format_data.get("limit"),
    )

    items = [TaskItem(id=i["id"], content=i["content"], expected=i.get("expected")) for i in data["items"]]

    known_keys = {"id", "type", "description", "eval", "format", "items"}
    extra_fields = {k: v for k, v in data.items() if k not in known_keys}

    return Task(
        id=data["id"],
        type=data["type"],
        description=data.get("description", ""),
        eval=eval_spec,
        format=format_spec,
        items=items,
        extra_fields=extra_fields,
    )


def load_tasks(paths: List[str | Path]) -> List[Task]:
    return [load_task(p) for p in paths]
