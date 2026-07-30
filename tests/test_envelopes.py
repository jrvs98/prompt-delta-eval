from pathlib import Path

import pytest

from promptdelta.envelopes import EnvelopeBook

ENVELOPES_PATH = Path(__file__).parent.parent / "configs" / "envelopes.yaml"


@pytest.fixture()
def book():
    return EnvelopeBook(ENVELOPES_PATH)


def test_bare_condition_is_untouched_content(book):
    rendered = book.render("math", "bare", "What is 2 + 2?")
    assert rendered == "What is 2 + 2?"


def test_engineered_condition_wraps_content(book):
    rendered = book.render("math", "engineered", "What is 2 + 2?")
    assert "What is 2 + 2?" in rendered
    assert len(rendered) > len("What is 2 + 2?")
    assert "step by step" in rendered.lower()


def test_all_conditions_preserve_original_content(book):
    content = "Some unique task content 12345"
    for condition in ("bare", "minimal", "engineered"):
        rendered = book.render("classification", condition, content)
        assert content in rendered


def test_unknown_condition_raises(book):
    with pytest.raises(ValueError):
        book.render("math", "nonexistent", "hello")


def test_unknown_task_type_raises(book):
    with pytest.raises(ValueError):
        book.render("nonexistent_type", "bare", "hello")


def test_extraction_schema_hint_placeholder(book):
    rendered = book.render(
        "extraction", "engineered", "Invoice text", extra_fields={"schema_hint": "name, date, amount"}
    )
    assert "name, date, amount" in rendered


def test_missing_placeholder_gives_helpful_error(book):
    with pytest.raises(ValueError, match="schema_hint"):
        book.render("extraction", "engineered", "Invoice text")
