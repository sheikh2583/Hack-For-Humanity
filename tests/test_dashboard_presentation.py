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
from app.streamlit_app import _export_csv, color_for_kiln, responsive_css


def test_colour_for_kiln_uses_three_priority_rank_bands() -> None:
    """Low, middle, and high ranks receive distinct marker colours."""
    candidates = pd.DataFrame({"priority_rank": [1, 2, 3]})
    display_bands = add_priority_bands(candidates)
    colours = {color_for_kiln(row) for _, row in display_bands.iterrows()}
    assert colours == {"red", "orange", "green"}


def test_flagged_count_uses_breach_count_or_configured_distance_fallback() -> None:
    """Rule-review counts use explicit breaches, then configured buffers."""
    from app.streamlit_app import _flagged_count

    rules = {"siting_rules": [{"feature": "schools", "buffer_m": 500}]}
    assert _flagged_count(pd.DataFrame({"breach_count": [0, 1, 2]}), rules) == 2
    frame = pd.DataFrame({"dist_schools_m": [499.0, 500.0, 900.0]})
    assert _flagged_count(frame, rules) == 1
    both_sources = pd.DataFrame({"rule_signals_count": [0, 0], "dist_schools_m": [600, 400]})
    assert _flagged_count(both_sources, rules) == 1


def test_candidate_csv_has_fixed_rule_columns_and_missing_layer_values() -> None:
    """Export distinguishes configured missing data from layers not mapped."""
    import app.streamlit_app as dashboard

    frame = pd.DataFrame({
        "kiln_id": ["k1"], "district": ["Dhaka"], "class": ["Zigzag"],
        "confidence": [0.8], "priority": [2.0], "priority_band": ["Medium"],
        "lat": [23.7], "lon": [90.4], "dist_schools_m": [float("nan")],
        "dist_hospitals_m": [1200.0], "dist_settlements_m": [300.0],
        "breach_count": [1], "detection_status": ["Known"],
    })
    exported = pd.read_csv(StringIO(dashboard._export_csv(frame)))
    assert exported.columns.tolist() == [
        "ID", "District", "Type", "Confidence_Pct", "Priority_Score", "Priority_Band",
        "Detection_Status", "Latitude", "Longitude", "Dist_School_m",
        "Dist_Hospital_m", "Dist_Railway_m", "Dist_Settlement_m", "Dist_Forest_m",
        "Dist_Water_m", "Rule_Signals_Count", "Flagged_For_Review", "Rule_Data_Notes",
        "Breach_Severity_Score", "Top_Rule_Signal",
    ]
    assert pd.isna(exported.loc[0, "Dist_School_m"])
    assert exported.loc[0, "Dist_Hospital_m"] == 1200.0
    assert pd.isna(exported.loc[0, "Dist_Railway_m"])
    assert bool(exported.loc[0, "Flagged_For_Review"])


def test_popup_shows_mapped_distances_and_missing_mapping(monkeypatch) -> None:
    """Popup shows configured distances and names unavailable map layers."""
    import app.streamlit_app as dashboard

    monkeypatch.setattr(dashboard, "load_config", lambda: {"rules": {"siting_rules": [
        {"id": "near_school", "feature": "schools", "buffer_m": 1000, "severity": 3},
        {"id": "near_hospital", "feature": "hospitals", "buffer_m": 1000, "severity": 3},
        {"id": "near_settlement", "feature": "settlements", "buffer_m": 1000, "severity": 2},
    ]}})
    monkeypatch.setattr(dashboard, "_report_from_json", lambda _row: None)
    row = pd.Series({
        "kiln_id": "k1", "lat": 23.7, "lon": 90.4, "class": "Zigzag",
        "priority_band": "Low", "district": "Dhaka", "dist_schools_m": 340.0,
        "dist_hospitals_m": 1200.0, "dist_forests_m": float("nan"),
    })
    popup = dashboard.build_popup(row)
    assert "Near school: 340 m" in popup
    assert "Near hospital: 1.2 km" in popup
    assert "Nearest forest: No mapping data" in popup


def test_popup_orders_rules_by_severity_and_marks_thresholds(monkeypatch) -> None:
    """Popup orders configured signals by severity and flags in-buffer distances."""
    import app.streamlit_app as dashboard

    monkeypatch.setattr(dashboard, "load_config", lambda: {"rules": {"siting_rules": [
        {"id": "near_settlement", "feature": "settlements", "buffer_m": 1000, "severity": 2},
        {"id": "near_school", "feature": "schools", "buffer_m": 1000, "severity": 3},
    ]}})
    monkeypatch.setattr(dashboard, "_report_from_json", lambda _row: None)
    row = pd.Series({
        "kiln_id": "k2", "lat": 23.7, "lon": 90.4, "class": "Zigzag",
        "priority_band": "High", "district": "Dhaka", "dist_schools_m": 340.0,
        "dist_settlements_m": 450.0,
    })
    popup = dashboard.build_popup(row)
    assert popup.index("Near school") < popup.index("Near settlement")
    assert "severity: critical" in popup
    assert "severity: moderate" in popup
    assert "340 m" in popup and "450 m" in popup and "⚠️" in popup


def test_popup_discloses_osm_wetland_proxy(monkeypatch) -> None:
    """An active wetland signal carries the requested proxy qualification."""
    import app.streamlit_app as dashboard

    monkeypatch.setattr(dashboard, "load_config", lambda: {"rules": {"siting_rules": [
        {"id": "near_wetland", "feature": "water", "buffer_m": 1000, "severity": 2},
    ]}})
    row = pd.Series({
        "kiln_id": "wet-1", "lat": 23.7, "lon": 90.4, "class": "Zigzag",
        "priority_band": "Medium", "district": "Dhaka", "dist_water_m": 800.0,
    })
    popup = dashboard.build_popup(row)
    assert "Near wetland: 800 m" in popup
    assert "Note: water layer is an OSM proxy. Legal definition requires land submerged" in popup


def test_district_summary_shows_most_common_rule_signal(monkeypatch) -> None:
    """District summary names the most common triggered configured rule."""
    import geopandas as gpd
    from shapely.geometry import Point

    import app.streamlit_app as dashboard

    monkeypatch.setattr(dashboard, "load_config", lambda: {"rules": {"siting_rules": [
        {"id": "near_school", "feature": "schools", "severity": 3},
        {"id": "near_settlement", "feature": "settlements", "severity": 2},
    ]}})
    rendered_metrics: list[tuple[str, object]] = []

    class Column:
        def metric(self, label: str, value: object) -> None:
            rendered_metrics.append((label, value))

    monkeypatch.setattr(dashboard.st, "columns", lambda _count: [Column() for _ in range(4)])
    monkeypatch.setattr(dashboard.st, "info", lambda _message: None)
    frame = gpd.GeoDataFrame(
        {
            "district": ["Dhaka", "Dhaka", "Dhaka"],
            "priority_band": ["High", "Medium", "Low"],
            "breached_rules": [["near_school"], ["near_school"], ["near_settlement"]],
        },
        geometry=[Point(90.4, 23.7), Point(90.41, 23.7), Point(90.42, 23.7)],
        crs="EPSG:4326",
    )
    dashboard.render_district_summary("Dhaka", frame)
    assert ("Top rule signal", "Near school") in rendered_metrics


def test_confidence_range_filters_candidates_before_map(monkeypatch) -> None:
    """The active confidence slider range removes out-of-range candidates."""
    import app.streamlit_app as dashboard

    monkeypatch.setattr(dashboard, "load_config", lambda: {"rules": {}})
    frame = pd.DataFrame(
        {
            "district": ["Dhaka"] * 3,
            "class": ["Zigzag"] * 3,
            "confidence": [0.2, 0.5, 0.9],
            "priority_band": ["Low", "Medium", "High"],
        }
    )
    filters = {
        "district": "All Districts",
        "kiln_type": "All types",
        "priorities": {"High", "Medium", "Low"},
        "confidence_range": (0.4, 0.7),
        "new_only": False,
    }
    filtered = dashboard._filtered(frame, filters)
    assert filtered["confidence"].tolist() == [0.5]


def test_responsive_css_contains_mobile_breakpoints_and_map_rules() -> None:
    """The dashboard CSS covers both requested phone breakpoints."""
    css = responsive_css()
    assert "@media (max-width: 768px)" in css
    assert "@media (max-width: 480px)" in css
    assert "min-height: 320px" in css
    assert "height: 60vh" in css
    assert '[data-testid="stMainBlockContainer"] h1.dhoa-brand-title' in css
    assert "padding: 0.38em 0 0.12em !important" in css
    assert "padding-top: 0.38em !important" in css


def test_header_marks_metrics_for_mobile_grid(monkeypatch) -> None:
    """Header metrics use the CSS hook for the narrow-screen two-column grid."""
    import app.streamlit_app as dashboard

    markup: list[str] = []
    monkeypatch.setattr(dashboard.st, "markdown", lambda value, **_kwargs: markup.append(value))
    monkeypatch.setattr(dashboard.st, "caption", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dashboard, "load_config", lambda: {"rules": {}})
    dashboard.render_header(
        pd.DataFrame({"priority_band": ["High"], "district": ["Dhaka"]})
    )
    assert any("h1 class='dhoa-brand-title'" in value for value in markup)
    assert any("class='dhoa-metrics'" in value for value in markup)


def test_folium_map_shows_every_priority_band_and_optional_heatmap(monkeypatch) -> None:
    """Default map keeps all synthetic candidates in visible severity layers."""
    import folium
    import geopandas as gpd
    from folium.plugins import HeatMap, MarkerCluster
    from shapely.geometry import Point

    import app.streamlit_app as dashboard

    monkeypatch.setattr(dashboard, "load_config", lambda: {"rules": {"siting_rules": []}})
    frame = gpd.GeoDataFrame(
        {
            "kiln_id": ["high-1", "medium-1", "low-1"],
            "lat": [23.70, 23.71, 23.72],
            "lon": [90.40, 90.41, 90.42],
            "class": ["Zigzag"] * 3,
            "district": ["Dhaka"] * 3,
            "confidence": [0.9, 0.8, 0.7],
            "priority_band": ["High", "Medium", "Low"],
            "priority": [3.0, 2.0, 1.0],
        },
        geometry=[Point(90.40, 23.70), Point(90.41, 23.71), Point(90.42, 23.72)],
        crs="EPSG:4326",
    )
    filters = {
        "district": "All Districts", "kiln_type": "All types",
        "map_style": "Street map", "priorities": {"High", "Medium", "Low"},
        "confidence_range": (0.0, 1.0), "signal_filters": {}, "new_only": False,
    }

    result = dashboard.build_map(frame, filters)
    assert isinstance(result, folium.Map)
    clusters = [item for item in result._children.values() if isinstance(item, MarkerCluster)]
    assert {cluster.layer_name for cluster in clusters} == {
        "High Priority", "Medium Priority", "Low Priority"
    }
    assert sum(len(cluster._children) for cluster in clusters) == 3
    heatmaps = [item for item in result._children.values() if isinstance(item, HeatMap)]
    assert len(heatmaps) == 1


def test_folium_marker_click_selects_candidate_for_report(monkeypatch) -> None:
    """A clicked Folium marker selects its kiln for the report panel."""
    import geopandas as gpd
    from shapely.geometry import Point

    import app.streamlit_app as dashboard

    session_state: dict[str, object] = {"dhoa_last_map_click_count": None}
    monkeypatch.setattr(dashboard.st, "session_state", session_state)
    monkeypatch.setattr(dashboard.st, "markdown", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dashboard.st, "info", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dashboard, "load_config", lambda: {"rules": {"siting_rules": []}})
    monkeypatch.setattr(
        dashboard,
        "st_folium",
        lambda *_args, **_kwargs: {
            "last_object_clicked": {"lat": 23.7, "lng": 90.4},
            "last_object_clicked_count": 1,
        },
    )
    selected_ids: list[str] = []
    monkeypatch.setattr(
        dashboard,
        "_render_selected_candidate",
        lambda row: selected_ids.append(str(row["kiln_id"])),
    )
    frame = gpd.GeoDataFrame(
        {
            "kiln_id": ["clicked-kiln"], "lat": [23.7], "lon": [90.4],
            "class": ["Zigzag"], "district": ["Dhaka"],
            "confidence": [0.9], "priority_band": ["High"], "priority": [2.0],
        },
        geometry=[Point(90.4, 23.7)],
        crs="EPSG:4326",
    )
    filters = {
        "district": "All Districts", "kiln_type": "All types",
        "map_style": "Street map", "priorities": {"High", "Medium", "Low"},
        "confidence_range": (0.0, 1.0), "signal_filters": {}, "new_only": False,
    }

    dashboard.render_map(frame, filters)
    assert session_state["selected_kiln_id"] == "clicked-kiln"
    assert selected_ids == ["clicked-kiln"]


def test_export_keeps_district_and_full_candidate_fields() -> None:
    """The dashboard export retains district and existing candidate fields."""
    result = _export_csv(
        pd.DataFrame(
            {
                "kiln_id": ["candidate-1"],
                "district": ["Gazipur"],
                "class": ["Zigzag"],
                "confidence": [0.8],
                "priority_band": ["Medium"],
                "breached_rules": [["near_school"]],
            }
        )
    )
    assert "District" in result.splitlines()[0]
    assert "Gazipur" in result


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
    assert result.startswith("# Dhoa advisory screening export.")
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
    assert result.startswith("# Dhoa advisory screening export.")
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
