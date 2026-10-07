"""Tests for safe dashboard popup attribute parsing."""

from app.popup import build_marker_popup, parse_candidate_signals


def test_parse_candidate_signals_accepts_serialized_string_lists() -> None:
    """A serialized string list becomes a list of rule identifiers."""
    assert parse_candidate_signals("['setback', 'technology']") == ["setback", "technology"]


def test_parse_candidate_signals_does_not_execute_input() -> None:
    """Expressions outside literal list data remain inert text."""
    assert parse_candidate_signals("[__import__('pathlib').Path('/tmp/x').touch()]") == [
        "[__import__('pathlib').Path('/tmp/x').touch()]"
    ]


def test_parse_candidate_signals_validates_list_items() -> None:
    """Non-string list members are rejected as a serialized value."""
    assert parse_candidate_signals("[1, 2]") == ["[1, 2]"]


def test_marker_popup_is_advisory_and_explains_mapped_distances() -> None:
    popup = build_marker_popup(
        {
            "kiln_id": "candidate-1",
            "class": "FCBK",
            "confidence": 0.91,
            "breach_score": 3,
            "breached_rules": ["near_school"],
            "dist_schools_m": 120.0,
            "signal_provenance_json": (
                '[{"signal_id":"near_school","review_state":"unverified_candidate",'
                '"source_layer_id":"openstreetmap:schools","source_authority":"OSM",'
                '"source_url":"https://www.openstreetmap.org/","feature_id":"way/123",'
                '"distance_m":120.0,"measurement_method":"polygon to mapped geometry"}]'
            ),
        },
        rank=1,
        total=2,
    )
    assert "Kiln candidate" in popup
    assert "Detector confidence" in popup
    assert "Candidate rule signals" in popup
    assert "unverified_candidate" in popup
    assert "way/123" in popup
    assert "mapped feature" in popup
    assert "legally controlling boundaries" in popup
    assert "not legal or administrative findings" in popup


def test_marker_popup_escapes_untrusted_feature_text() -> None:
    popup = build_marker_popup(
        {
            "kiln_id": "<script>alert(1)</script>",
            "class": "<img src=x>",
            "confidence": 0.5,
            "breached_rules": [],
            "signal_provenance_json": "[]",
        },
        rank=1,
        total=1,
    )
    assert "<script>" not in popup
    assert "&lt;script&gt;" in popup


def test_legacy_signal_popup_marks_missing_provenance_explicitly() -> None:
    """Old scored GeoParquet still shows each signal as unverified and traceable gap."""
    popup = build_marker_popup(
        {
            "kiln_id": "legacy-1",
            "class": "Zigzag",
            "confidence": 0.8,
            "breached_rules": ["near_school"],
        },
        rank=1,
        total=1,
    )
    assert "near_school" in popup
    assert "unverified_candidate" in popup
    assert "Not retained in this legacy dataset" in popup
    assert "missing provenance is not evidence" in popup
