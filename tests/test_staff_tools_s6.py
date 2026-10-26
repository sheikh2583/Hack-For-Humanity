"""S6 route-link tests using a tiny synthetic sequence of WGS84 stops.

Input schema: ordered latitude/longitude pairs. Output schema: URL-encoded
Google Maps route links that preserve all stops in their original order.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from app.staff_tools import google_maps_route_links


def test_route_links_cover_synthetic_stops_in_order_with_platform_sized_chunks() -> None:
    """Eight synthetic points make two routes, sharing the segment boundary."""
    stops = [(23.0 + index / 100, 90.0 + index / 100) for index in range(8)]
    links = google_maps_route_links(stops)

    assert [(link.first_stop, link.last_stop) for link in links] == [(1, 5), (5, 8)]
    first = parse_qs(urlparse(links[0].url).query)
    second = parse_qs(urlparse(links[1].url).query)
    assert first["origin"] == ["23.000000,90.000000"]
    assert first["destination"] == ["23.040000,90.040000"]
    assert first["waypoints"] == ["23.010000,90.010000|23.020000,90.020000|23.030000,90.030000"]
    assert second["origin"] == ["23.040000,90.040000"]
    assert second["destination"] == ["23.070000,90.070000"]


def test_route_link_rejects_invalid_synthetic_coordinates() -> None:
    """Invalid or non-finite points are rejected instead of entering route URLs."""
    with pytest.raises(ValueError):
        google_maps_route_links([(float("nan"), 90.0)])
    with pytest.raises(ValueError):
        google_maps_route_links([(91.0, 90.0)])
