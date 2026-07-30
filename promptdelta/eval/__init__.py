from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from . import objective
from .format_check import check_format
from .llm_judge import judge_score

if TYPE_CHECKING:
    from ..providers.base import Provider
    from ..tasks import Task, TaskItem


def evaluate(
    task: "Task",
    item: "TaskItem",
    output_text: str,
    judge_provider: Optional["Provider"] = None,
) -> Tuple[float, Dict[str, Any], bool, Dict[str, Any]]:
    """Returns (score 0-1, eval_details, format_ok, format_details)."""
    method = task.eval.method

    if method == "exact_match":
        score, details = objective.score_exact_match(output_text, item.expected, task.eval.normalize)
    elif method == "numeric_tolerance":
        score, details = objective.score_numeric_tolerance(output_text, item.expected, task.eval.tolerance)
    elif method == "regex":
        score, details = objective.score_regex(output_text, str(item.expected))
    elif method == "json_schema":
        score, details = objective.score_json_schema(output_text, task.eval.required_keys)
    elif method == "llm_judge":
        if judge_provider is None:
            score, details = 0.0, {"judge_error": "no judge provider configured for this experiment"}
        else:
            score, details = judge_score(judge_provider, item.content, task.eval.rubric, output_text)
    else:
        raise ValueError(f"Unknown eval method: {method}")

    format_ok, format_details = check_format(
        output_text, task.format.rule, count=task.format.count, limit=task.format.limit
    )

    return score, details, format_ok, format_details


__all__ = ["evaluate"]
