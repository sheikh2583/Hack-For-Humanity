"""Tests for safe dashboard popup attribute parsing."""

from app.popup import parse_breached_rules


def test_parse_breached_rules_accepts_serialized_string_lists() -> None:
    """A serialized string list becomes a list of rule identifiers."""
    assert parse_breached_rules("['setback', 'technology']") == ["setback", "technology"]


def test_parse_breached_rules_does_not_execute_input() -> None:
    """Expressions outside literal list data remain inert text."""
    assert parse_breached_rules("[__import__('pathlib').Path('/tmp/x').touch()]") == [
        "[__import__('pathlib').Path('/tmp/x').touch()]"
    ]


def test_parse_breached_rules_validates_list_items() -> None:
    """Non-string list members are rejected as a serialized value."""
    assert parse_breached_rules("[1, 2]") == ["[1, 2]"]
