"""Pure helpers for Inspector-only route links.

Input schema: ordered WGS84 ``(latitude, longitude)`` stops from assigned kiln
rows. Output schema: Google Maps Directions URLs split into supported groups
of five stops, preserving every stop and the requested order.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from collections.abc import Sequence
from urllib.parse import urlencode


GOOGLE_MAPS_STOPS_PER_ROUTE = 5


@dataclass(frozen=True)
class RouteLink:
    """One ordered Google Maps route and its inclusive one-based stop span."""

    first_stop: int
    last_stop: int
    url: str


def google_maps_route_links(stops: Sequence[tuple[float, float]]) -> list[RouteLink]:
    """Build sequential route links without dropping assigned WGS84 stops.

    Input: a sequence of finite latitude/longitude pairs. Output: no links for
    no stops, a destination link for one stop, otherwise direction links split
    at five stops with the previous segment's last stop reused as the next
    origin. Google Maps decides the road route; this helper only encodes stops.
    """
    normalized = [(float(lat), float(lon)) for lat, lon in stops]
    if any(not math.isfinite(lat) or not math.isfinite(lon) for lat, lon in normalized):
        raise ValueError("route stops must contain finite coordinates")
    if any(not -90 <= lat <= 90 or not -180 <= lon <= 180 for lat, lon in normalized):
        raise ValueError("route stops must be valid WGS84 coordinates")
    if not normalized:
        return []
    links: list[RouteLink] = []
    start = 0
    while start < len(normalized):
        end = min(start + GOOGLE_MAPS_STOPS_PER_ROUTE, len(normalized))
        segment = normalized[start:end]
        if len(segment) == 1:
            params = {"api": "1", "destination": _coordinate(segment[0])}
        else:
            params = {
                "api": "1",
                "origin": _coordinate(segment[0]),
                "destination": _coordinate(segment[-1]),
                "travelmode": "driving",
            }
            if len(segment) > 2:
                params["waypoints"] = "|".join(_coordinate(point) for point in segment[1:-1])
        url = "https://www.google.com/maps/dir/?" + urlencode(params)
        links.append(RouteLink(start + 1, end, url))
        if end == len(normalized):
            break
        start = end - 1
    return links


def _coordinate(point: tuple[float, float]) -> str:
    """Format one point for a URL query value."""
    return f"{point[0]:.6f},{point[1]:.6f}"
