from __future__ import annotations

import json
import re
from typing import Any, Dict, Tuple

from .objective import _strip_code_fences  # reuse fence stripping


def check_format(output: str, rule: str, count: int | None = None, limit: int | None = None) -> Tuple[bool, Dict[str, Any]]:
    """Returns (format_ok, details). `rule='none'` always passes."""
    text = output.strip()

    if rule == "none":
        return True, {}

    if rule == "one_word":
        words = text.split()
        ok = len(words) == 1
        return ok, {"word_count": len(words)}

    if rule == "bullet_count":
        lines = [ln for ln in text.splitlines() if ln.strip()]
        bullet_lines = [ln for ln in lines if re.match(r"^\s*[-*•]\s+", ln)]
        ok = count is not None and len(bullet_lines) == count
        return ok, {"bullet_count": len(bullet_lines), "expected_count": count}

    if rule == "json":
        cleaned = _strip_code_fences(text)
        try:
            json.loads(cleaned)
            return True, {"valid_json": True}
        except json.JSONDecodeError as exc:
            return False, {"valid_json": False, "error": str(exc)}

    if rule == "word_limit":
        words = text.split()
        ok = limit is not None and len(words) <= limit
        return ok, {"word_count": len(words), "limit": limit}

    raise ValueError(f"Unknown format rule: {rule}")
