from __future__ import annotations

import json
import re
from typing import Any, Dict, Tuple

_NUMBER_RE = re.compile(r"-?\d[\d,]*\.?\d*")


def _extract_last_number(text: str) -> float | None:
    matches = _NUMBER_RE.findall(text)
    if not matches:
        return None
    try:
        return float(matches[-1].replace(",", ""))
    except ValueError:
        return None


def score_exact_match(output: str, expected: Any, normalize: bool = True) -> Tuple[float, Dict[str, Any]]:
    out = output.strip()
    exp = str(expected).strip()
    if normalize:
        out_cmp, exp_cmp = out.lower(), exp.lower()
    else:
        out_cmp, exp_cmp = out, exp
    correct = out_cmp == exp_cmp
    return (1.0 if correct else 0.0), {"expected": exp, "got": out, "correct": correct}


def score_numeric_tolerance(output: str, expected: Any, tolerance: float = 0.01) -> Tuple[float, Dict[str, Any]]:
    got = _extract_last_number(output)
    try:
        exp = float(expected)
    except (TypeError, ValueError):
        return 0.0, {"expected": expected, "got": got, "correct": False, "note": "expected value not numeric"}
    if got is None:
        return 0.0, {"expected": exp, "got": None, "correct": False, "note": "no number found in output"}
    correct = abs(got - exp) <= tolerance
    return (1.0 if correct else 0.0), {"expected": exp, "got": got, "correct": correct, "diff": abs(got - exp)}


def score_regex(output: str, expected_pattern: str) -> Tuple[float, Dict[str, Any]]:
    match = re.search(expected_pattern, output)
    correct = match is not None
    return (1.0 if correct else 0.0), {"pattern": expected_pattern, "matched": correct}


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"```$", "", text.strip())
    return text.strip()


def score_json_schema(output: str, required_keys: list[str]) -> Tuple[float, Dict[str, Any]]:
    cleaned = _strip_code_fences(output)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return 0.0, {"valid_json": False, "error": str(exc)}
    if not isinstance(parsed, dict):
        return 0.0, {"valid_json": True, "is_object": False}
    present = [k for k in required_keys if k in parsed]
    missing = [k for k in required_keys if k not in parsed]
    score = len(present) / len(required_keys) if required_keys else 1.0
    return score, {"valid_json": True, "is_object": True, "present_keys": present, "missing_keys": missing}
