from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any, Dict, Tuple

if TYPE_CHECKING:
    from ..providers.base import Provider

_JUDGE_TEMPLATE = """You are an impartial evaluator. You will be shown a source text, a rubric, \
and a candidate response. Score the candidate response according to the rubric on a \
scale of 1 (worst) to 5 (best).

Rubric:
{rubric}

Source text:
{source}

Candidate response:
{response}

Respond with ONLY a JSON object in this exact form, nothing else:
{{"score": <integer 1-5>, "reasoning": "<one sentence>"}}
"""

_SCORE_FALLBACK_RE = re.compile(r'"?score"?\s*[:=]\s*(\d)')


def judge_score(
    judge_provider: "Provider",
    source_text: str,
    rubric: str,
    response_text: str,
) -> Tuple[float, Dict[str, Any]]:
    """Returns (normalized_score_0_to_1, details). Falls back to a regex
    scrape of the judge's raw output if it doesn't return clean JSON.
    """
    prompt = _JUDGE_TEMPLATE.format(rubric=rubric.strip(), source=source_text.strip(), response=response_text.strip())
    result = judge_provider.complete(prompt, temperature=0.0, max_tokens=200)

    if result.error:
        return 0.0, {"judge_error": result.error}

    raw = result.text.strip()
    cleaned = re.sub(r"^```[a-zA-Z]*\n?|```$", "", raw).strip()

    score = None
    reasoning = ""
    try:
        parsed = json.loads(cleaned)
        score = int(parsed.get("score"))
        reasoning = str(parsed.get("reasoning", ""))
    except (json.JSONDecodeError, TypeError, ValueError):
        m = _SCORE_FALLBACK_RE.search(raw)
        if m:
            score = int(m.group(1))
            reasoning = "(parsed via fallback regex — judge did not return clean JSON)"

    if score is None:
        return 0.0, {"judge_error": "could not parse a score from judge output", "judge_raw": raw}

    score = max(1, min(5, score))
    normalized = (score - 1) / 4.0  # map 1-5 -> 0-1
    return normalized, {"raw_score": score, "reasoning": reasoning}
