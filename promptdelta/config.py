from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .envelopes import VALID_CONDITIONS


@dataclass
class ModelSpec:
    provider: str
    model: str
    label: Optional[str] = None          # display name, defaults to "provider:model"
    generation_rank: Optional[float] = None  # optional: lets the report sort/plot models by "how new" they are
    params: Dict[str, Any] = field(default_factory=dict)  # passed through to the provider constructor

    def display_name(self) -> str:
        return self.label or f"{self.provider}:{self.model}"


@dataclass
class JudgeSpec:
    provider: str
    model: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Experiment:
    name: str
    conditions: List[str]
    models: List[ModelSpec]
    task_paths: List[str]
    runs_per_cell: int = 3
    temperature: float = 0.7
    max_tokens: int = 1024
    envelopes_path: str = "configs/envelopes.yaml"
    judge: Optional[JudgeSpec] = None
    db_path: str = "results/results.db"
    report_path: str = "results/report.html"
    config_dir: Path = field(default_factory=Path)  # base dir for resolving relative task paths


def load_experiment(path: str | Path) -> Experiment:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    exp = data.get("experiment")
    if exp is None:
        raise ValueError(f"Config {path} must have a top-level 'experiment:' key.")

    required = ("name", "conditions", "models", "tasks")
    missing = [k for k in required if k not in exp]
    if missing:
        raise ValueError(f"Experiment config is missing required field(s): {missing}")

    conditions = exp["conditions"]
    bad = [c for c in conditions if c not in VALID_CONDITIONS]
    if bad:
        raise ValueError(f"Unknown condition(s) {bad}. Must be a subset of {VALID_CONDITIONS}.")

    models = [
        ModelSpec(
            provider=m["provider"],
            model=m["model"],
            label=m.get("label"),
            generation_rank=m.get("generation_rank"),
            params=m.get("params", {}) or {},
        )
        for m in exp["models"]
    ]

    judge = None
    if "judge" in exp and exp["judge"]:
        j = exp["judge"]
        judge = JudgeSpec(provider=j["provider"], model=j["model"], params=j.get("params", {}) or {})
    # If no judge is configured but a loaded task uses eval.method: llm_judge,
    # runner.py raises a clear error at run time (tasks aren't loaded yet here).

    output = exp.get("output", {}) or {}

    return Experiment(
        name=exp["name"],
        conditions=conditions,
        models=models,
        task_paths=exp["tasks"],
        runs_per_cell=exp.get("runs_per_cell", 3),
        temperature=exp.get("temperature", 0.7),
        max_tokens=exp.get("max_tokens", 1024),
        envelopes_path=exp.get("envelopes", "configs/envelopes.yaml"),
        judge=judge,
        db_path=output.get("db_path", "results/results.db"),
        report_path=output.get("report_path", "results/report.html"),
        config_dir=path.parent,
    )
