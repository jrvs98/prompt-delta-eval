from promptdelta.eval import format_check, objective


def test_exact_match_case_insensitive_by_default():
    score, details = objective.score_exact_match("Positive", "positive")
    assert score == 1.0
    assert details["correct"] is True


def test_exact_match_fails_on_extra_words():
    score, _ = objective.score_exact_match("I think it's positive", "positive")
    assert score == 0.0


def test_numeric_tolerance_within_bound():
    score, details = objective.score_numeric_tolerance("The answer is 40.0 mph.", 40, tolerance=0.5)
    assert score == 1.0
    assert details["got"] == 40.0


def test_numeric_tolerance_outside_bound():
    score, _ = objective.score_numeric_tolerance("The answer is 41.0 mph.", 40, tolerance=0.01)
    assert score == 0.0


def test_numeric_tolerance_no_number_found():
    score, details = objective.score_numeric_tolerance("I don't know.", 40)
    assert score == 0.0
    assert details["got"] is None


def test_json_schema_all_keys_present():
    score, details = objective.score_json_schema('{"name": "A", "date": "2024-01-01", "amount": 5}', ["name", "date", "amount"])
    assert score == 1.0
    assert details["missing_keys"] == []


def test_json_schema_partial_keys():
    score, details = objective.score_json_schema('{"name": "A"}', ["name", "date", "amount"])
    assert 0 < score < 1
    assert "date" in details["missing_keys"]


def test_json_schema_invalid_json():
    score, details = objective.score_json_schema("not json at all", ["name"])
    assert score == 0.0
    assert details["valid_json"] is False


def test_json_schema_strips_code_fences():
    score, _ = objective.score_json_schema('```json\n{"name": "A"}\n```', ["name"])
    assert score == 1.0


def test_format_one_word_pass():
    ok, _ = format_check.check_format("positive", "one_word")
    assert ok is True


def test_format_one_word_fail():
    ok, _ = format_check.check_format("it is positive", "one_word")
    assert ok is False


def test_format_bullet_count_exact():
    ok, details = format_check.check_format("- a\n- b\n- c", "bullet_count", count=3)
    assert ok is True
    assert details["bullet_count"] == 3


def test_format_bullet_count_wrong_number():
    ok, _ = format_check.check_format("- a\n- b", "bullet_count", count=3)
    assert ok is False


def test_format_json_pass():
    ok, _ = format_check.check_format('{"a": 1}', "json")
    assert ok is True


def test_format_json_fail():
    ok, _ = format_check.check_format("not json", "json")
    assert ok is False


def test_format_none_always_passes():
    ok, _ = format_check.check_format("literally anything", "none")
    assert ok is True
