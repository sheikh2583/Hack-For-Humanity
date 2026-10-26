"""S3 public Near me card rendering.

Input schema: tiny synthetic public candidate rows with coordinates, display
type/area, nearest place, and distance. Output schema: localized cards and
directions links without any priority fields or labels.
"""

from __future__ import annotations

from contextlib import nullcontext

import pandas as pd

import app.streamlit_app as dashboard
import app.kiln_data as kd


def test_public_result_cards_show_place_distance_type_and_directions(monkeypatch) -> None:
    """A single synthetic kiln becomes a public card with no priority content."""
    captured: list[object] = []

    class FakeStreamlit:
        def container(self, **kwargs):
            return nullcontext()

        def markdown(self, value):
            captured.append(value)

        def caption(self, value):
            captured.append(value)

        def link_button(self, label, url, **kwargs):
            captured.extend((label, url))

        def button(self, label, **kwargs):
            captured.append(label)

    monkeypatch.setattr(dashboard, "st", FakeStreamlit())
    frame = pd.DataFrame([{
        "lat": 23.8, "lon": 90.2, "ui_type": "Zigzag", "ui_area": "Savar",
        "nearest_place": "Amin Bazar", "distance_m": 1250,
    }])

    dashboard._render_community_cards(frame, show_distance=True)

    rendered = " ".join(map(str, captured))
    assert "Zigzag" in rendered
    assert "Amin Bazar" in rendered
    assert "1,250" in rendered
    assert "maps/dir/" in rendered
    assert "priority" not in rendered.casefold()


def test_public_map_clusters_use_the_neutral_public_marker_color() -> None:
    """Public clusters share one neutral fill and do not expose a priority palette."""
    frame = pd.DataFrame([{
        "lat": 23.8, "lon": 90.2, "ui_type": "Zigzag", "ui_area": "Savar",
    }])
    payload = kd.public_marker_payload(frame)
    map_html = dashboard._marker_map(frame, "street", None, payload=payload, public=True).get_root().render()
    assert "dhoa-cluster-neutral" in map_html
    assert "background:#9aa7b4" in map_html
