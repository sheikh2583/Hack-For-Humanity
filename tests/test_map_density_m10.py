"""Clustering split zoom and the density (heat) layer."""

from __future__ import annotations

import app.streamlit_app as dashboard


def test_clusters_split_one_zoom_step_later_and_selected_kiln_stays_visible() -> None:
    assert dashboard.CLUSTER_DISABLE_ZOOM == 13
    assert dashboard._MARKER_OPTIONS["disableClusteringAtZoom"] == 13
    assert dashboard.SELECTED_ZOOM >= dashboard.CLUSTER_DISABLE_ZOOM


def test_base_map_loads_the_heat_plugin_so_the_overlay_can_work() -> None:
    html = dashboard._new_map("street", None).get_root().render()
    assert "leaflet-heat" in html


def test_density_overlay_renders_a_heat_layer_and_is_optional() -> None:
    assert dashboard._selected_feature_group(None, None, None) is None
    group = dashboard._selected_feature_group(None, None, [[23.8, 90.4], [23.81, 90.41]])
    map_view = dashboard._new_map("street", None)
    group.add_to(map_view)
    assert "heatLayer" in map_view.get_root().render()
