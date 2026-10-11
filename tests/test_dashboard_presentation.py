"""Tests for user-facing screening terms and CSV export schema."""

from __future__ import annotations

from io import StringIO

import pandas as pd

from app.dashboard_filters import add_priority_bands
from app.presentation import (
    DASHBOARD_LABELS,
    DETAIL_COLUMN_RENAMES,
    marker_tooltip,
    screening_csv,
)
from app.streamlit_app import color_for_kiln


def test_colour_for_kiln_uses_three_priority_rank_bands() -> None:
    """Low, middle, and high ranks receive distinct marker colours."""
    candidates = pd.DataFrame({"priority_rank": [1, 2, 3]})
    display_bands = add_priority_bands(candidates)
    colours = {color_for_kiln(row) for _, row in display_bands.iterrows()}
    assert colours == {"red", "orange", "green"}


def test_colour_for_kiln_handles_tied_ranks_across_three_bands() -> None:
    """When many rows share the same priority_rank (method='min' ties),
    banding must still produce High/Medium/Low rather than all-High."""
    # Simulate real data: 3 distinct ranks + 6 rows tied at rank 3
    candidates = pd.DataFrame({"priority_rank": [1, 2, 3, 3, 3, 3, 3, 3, 3]})
    display_bands = add_priority_bands(candidates)
    colours = {color_for_kiln(row) for _, row in display_bands.iterrows()}
    assert colours == {"red", "orange", "green"}, (
        f"Expected three distinct colours but got {colours}; "
        f"bands: {display_bands['priority_band'].value_counts().to_dict()}"
    )


def test_dashboard_labels_are_non_conclusive() -> None:
    """Configured visible dashboard labels describe candidate screening only."""
    visible = " ".join(DASHBOARD_LABELS.values()).casefold()
    for prohibited in ("breach", "illegal", "non-compliant", "verified"):
        assert prohibited not in visible
    assert "candidate" in visible
    assert "screening" in visible
    assert "screening outputs" in DASHBOARD_LABELS["advisory"].casefold()
    assert "legally controlling boundaries" in DASHBOARD_LABELS["advisory"]
    table_columns = " ".join(DETAIL_COLUMN_RENAMES.values()).casefold()
    for prohibited in ("breach", "illegal", "non-compliant", "verified"):
        assert prohibited not in table_columns
    assert "candidate_rule_signals" in table_columns
    assert "signal_provenance" in table_columns


def test_dashboard_does_not_render_the_developer_banner(monkeypatch) -> None:
    """The removed developer-facing advisory is not displayed by the dashboard."""
    import app.streamlit_app as dashboard

    monkeypatch.setattr(dashboard, "dashboard_kilns_file", lambda: None)
    warnings: list[str] = []
    monkeypatch.setattr(dashboard.st, "set_page_config", lambda **kwargs: None)
    monkeypatch.setattr(dashboard.st, "title", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        dashboard.st, "warning", lambda message, **kwargs: warnings.append(message)
    )
    monkeypatch.setattr(dashboard.st, "info", lambda *args, **kwargs: None)
    dashboard.main()
    assert warnings == []


def test_marker_tooltip_keeps_model_confidence_separate() -> None:
    """Map tooltip labels detector confidence and candidate priority separately."""
    tooltip = marker_tooltip(pd.Series({"class": "FCBK", "confidence": 0.92}), 4)
    assert tooltip == "Screening priority #4 | Kiln candidate | FCBK | detector 92%"
    for prohibited in ("breach", "illegal", "non-compliant", "verified"):
        assert prohibited not in tooltip.casefold()


def test_csv_has_advisory_notice_and_non_conclusive_columns() -> None:
    """CSV notice, legacy-column mappings, and signal provenance are preserved."""
    frame = pd.DataFrame(
        {
            "kiln_id": ["candidate-1"],
            "breached_rules": [["near_school"]],
            "breach_count": [1],
            "breach_score": [3.0],
            "priority": [4.2],
            "priority_rank": [1],
            "technology_flagged": [False],
            "rules_version": ["draft-x"],
            "rules_verified": [False],
            "class": ["FCBK"],
            "confidence": [0.9],
            "dist_schools_m": [120.0],
            "signal_provenance_json": [
                [{"review_state": "unverified_candidate", "source_layer_id": "openstreetmap:schools"}]
            ],
            "geometry": [None],
        }
    )

    result = screening_csv(frame)
    assert result.startswith("# KilnWatch BD advisory screening export.")
    assert "legally controlling boundaries" in result
    exported = pd.read_csv(StringIO(result), comment="#")
    assert {
        "advisory_use_notice",
        "candidate_rule_signals",
        "candidate_rule_signal_count",
        "screening_score",
        "screening_priority",
        "screening_priority_rank",
        "technology_candidate_signal",
        "rule_config_version",
        "detected_class",
        "detector_confidence",
        "distance_to_mapped_schools_m",
        "signal_provenance_json",
    }.issubset(exported.columns)
    lowered = " ".join(exported.columns).casefold()
    for prohibited in ("breach", "illegal", "non-compliant", "verified"):
        assert prohibited not in lowered
    assert "rules_verified" not in exported.columns
    assert "unscreened_candidate" in exported.loc[0, "signal_provenance_json"]


def test_empty_csv_still_has_advisory_preamble() -> None:
    """An empty selection still downloads with an advisory-use statement."""
    result = screening_csv(pd.DataFrame(columns=["kiln_id", "geometry"]))
    assert result.startswith("# KilnWatch BD advisory screening export.")
    assert "screening candidates for human review" in result


def test_legacy_rows_get_explicit_missing_provenance_records() -> None:
    """Older pipeline Parquet files export signals as unverified with gaps stated."""
    result = screening_csv(
        pd.DataFrame({"kiln_id": ["old-1"], "breached_rules": [["near_school"]]})
    )
    exported = pd.read_csv(StringIO(result), comment="#")
    provenance = exported.loc[0, "signal_provenance_json"]
    assert "unscreened_candidate" in provenance
    assert "near_school" in provenance
    assert "Not retained in this legacy dataset" in provenance
    assert "missing provenance is not evidence" in provenance
