from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .storage import fetch_all


@dataclass
class CellStats:
    model_label: str
    task_id: str
    condition: str
    n: int
    mean_score: Optional[float]
    std_score: Optional[float]
    format_ok_rate: Optional[float]
    n_errors: int


@dataclass
class ModelTaskDelta:
    model_label: str
    task_id: str
    baseline_condition: str
    compare_condition: str
    baseline_mean: Optional[float]
    compare_mean: Optional[float]
    delta: Optional[float]           # compare_mean - baseline_mean
    cohens_d: Optional[float]


@dataclass
class Summary:
    experiment: str
    cells: List[CellStats]
    deltas: List[ModelTaskDelta]
    model_overall_delta: Dict[str, float]  # model_label -> mean delta across tasks (engineered - bare)
    conditions: List[str]
    models_order: List[str]              # models in the order they appeared in config / generation_rank if given


def _mean(xs: List[float]) -> Optional[float]:
    return statistics.mean(xs) if xs else None


def _std(xs: List[float]) -> Optional[float]:
    return statistics.pstdev(xs) if len(xs) > 1 else (0.0 if xs else None)


def _pooled_cohens_d(a: List[float], b: List[float]) -> Optional[float]:
    if len(a) < 2 or len(b) < 2:
        return None
    sa, sb = statistics.pstdev(a), statistics.pstdev(b)
    na, nb = len(a), len(b)
    pooled = (((na - 1) * sa**2 + (nb - 1) * sb**2) / (na + nb - 2)) ** 0.5 if (na + nb - 2) > 0 else 0.0
    if pooled == 0:
        return None
    return (statistics.mean(b) - statistics.mean(a)) / pooled


def summarize(db_path: str | Path, experiment: str, conditions: List[str], model_order: List[str]) -> Summary:
    rows = fetch_all(db_path, experiment)

    # group raw scores: (model_label, task_id, condition) -> list of scores
    grouped: Dict[tuple, List[float]] = {}
    format_grouped: Dict[tuple, List[int]] = {}
    error_counts: Dict[tuple, int] = {}

    for r in rows:
        key = (r["model_label"], r["task_id"], r["condition"])
        error_counts.setdefault(key, 0)
        if r["error"]:
            error_counts[key] += 1
            continue
        if r["score"] is not None:
            grouped.setdefault(key, []).append(r["score"])
        if r["format_ok"] is not None:
            format_grouped.setdefault(key, []).append(r["format_ok"])

    all_keys = set(grouped) | set(format_grouped) | set(error_counts)
    cells: List[CellStats] = []
    for (model_label, task_id, condition) in sorted(all_keys):
        scores = grouped.get((model_label, task_id, condition), [])
        fmts = format_grouped.get((model_label, task_id, condition), [])
        cells.append(
            CellStats(
                model_label=model_label,
                task_id=task_id,
                condition=condition,
                n=len(scores),
                mean_score=_mean(scores),
                std_score=_std(scores),
                format_ok_rate=(sum(fmts) / len(fmts)) if fmts else None,
                n_errors=error_counts.get((model_label, task_id, condition), 0),
            )
        )

    # deltas: baseline is "bare", compare against the richest available condition
    baseline_condition = "bare" if "bare" in conditions else conditions[0]
    compare_condition = "engineered" if "engineered" in conditions else conditions[-1]

    task_ids = sorted({c.task_id for c in cells})
    model_labels = sorted({c.model_label for c in cells})

    deltas: List[ModelTaskDelta] = []
    model_overall_delta: Dict[str, float] = {}

    for model_label in model_labels:
        per_task_deltas = []
        for task_id in task_ids:
            base_scores = grouped.get((model_label, task_id, baseline_condition), [])
            cmp_scores = grouped.get((model_label, task_id, compare_condition), [])
            base_mean = _mean(base_scores)
            cmp_mean = _mean(cmp_scores)
            delta = (cmp_mean - base_mean) if (base_mean is not None and cmp_mean is not None) else None
            d = _pooled_cohens_d(base_scores, cmp_scores)
            deltas.append(
                ModelTaskDelta(
                    model_label=model_label,
                    task_id=task_id,
                    baseline_condition=baseline_condition,
                    compare_condition=compare_condition,
                    baseline_mean=base_mean,
                    compare_mean=cmp_mean,
                    delta=delta,
                    cohens_d=d,
                )
            )
            if delta is not None:
                per_task_deltas.append(delta)
        if per_task_deltas:
            model_overall_delta[model_label] = statistics.mean(per_task_deltas)

    # order models: config order (model_order) first, fall back to alpha for
    # any not found there (shouldn't normally happen)
    ordered_models = [m for m in model_order if m in model_labels] + [
        m for m in model_labels if m not in model_order
    ]

    return Summary(
        experiment=experiment,
        cells=cells,
        deltas=deltas,
        model_overall_delta=model_overall_delta,
        conditions=conditions,
        models_order=ordered_models,
    )
