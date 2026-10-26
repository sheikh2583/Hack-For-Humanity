"""Streamlit-free logic for the Community view (module M5).

Input schema
------------
A prepared kiln ``pandas.DataFrame`` (see ``kiln_data.prepare_display_frame``)
with numeric ``lat`` / ``lon`` (WGS84 degrees), ``district``, ``upazila``,
optional ``nearest_place`` and ``priority_band`` (High / Medium / Low).

Output schema
-------------
* ``build_places`` -> list of ``Place`` (district, upazila, named place), each
  with a stable ``key``, a Bangla ``label`` that includes the kiln count, and a
  WGS84 centre. Only places that have kilns are offered, so a valid choice can
  never be empty for lack of data.
* ``search`` -> ``SearchResult``: kilns (with ``distance_m``, nearest first),
  the centre, the radius (``None`` = whole area), and the summary counts.
* ``nearest_beyond`` / ``next_radius`` / ``covered_district``: building blocks
  for the empty state ("nearest is 2.3 km away; show within 5 km") and for the
  "outside the covered districts" message.
* ``geocode_bangladesh``: optional free-text fallback with an injectable
  provider list, a process-wide rate limit and Bangladesh-only filtering.

Distances are measured in the projected CRS chosen by ``src.geo.crs`` via
``kiln_data.distances_from_point_m``; no legal threshold appears here.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

try:  # imported as ``app.community`` (tests) or as ``community`` (Streamlit)
    from app import kiln_data as kd
except ImportError:  # pragma: no cover - Streamlit adds app/ to sys.path
    import kiln_data as kd  # type: ignore[no-redef]

#: Radius choices offered to the user, in metres, and the default.
RADIUS_CHOICES_M: tuple[int, ...] = (1000, 2000, 5000, 10000)
DEFAULT_RADIUS_M = 5000

#: Margin around each district's kiln bounding box when deciding whether a
#: point is "inside a covered district". UI heuristic (the data has no district
#: polygons); it equals the largest radius choice. Owner should confirm.
COVERAGE_MARGIN_M = max(RADIUS_CHOICES_M)

#: Coarse bounding box of Bangladesh (lat_min, lat_max, lon_min, lon_max), used
#: only to discard geocoder hits that are clearly in another country.
BANGLADESH_BBOX = (20.5, 26.7, 88.0, 92.8)

KIND_DISTRICT = "district"
KIND_UPAZILA = "upazila"
KIND_NAMED = "named"
KIND_POINT = "point"  # free-text geocode or GPS fix


@dataclass(frozen=True)
class Place:
    """One selectable search origin.

    ``radius_applies`` is False for whole-area choices (district, upazila),
    which list every kiln in the area instead of a radius.
    """

    key: str
    kind: str
    name: str
    label: str
    lat: float
    lon: float
    district: str = ""
    upazila: str = ""
    kiln_count: int = 0

    @property
    def radius_applies(self) -> bool:
        """True when a radius is meaningful for this origin."""
        return self.kind in (KIND_NAMED, KIND_POINT)


@dataclass
class SearchResult:
    """Kilns found for one origin. ``rows`` is sorted by ``distance_m``."""

    place: Place
    rows: pd.DataFrame
    radius_m: int | None
    summary: dict[str, int] = field(default_factory=dict)

    @property
    def empty(self) -> bool:
        """True when no kiln matched."""
        return self.rows.empty


# --------------------------------------------------------------------------
# Places
# --------------------------------------------------------------------------
def _clean(value: object) -> str:
    """Return a stripped string, or '' for missing/NaN-like values."""
    text = "" if value is None else str(value).strip()
    return "" if text.lower() in {"nan", "none", "<na>", "nat"} else text


def _centre(frame: pd.DataFrame) -> tuple[float, float]:
    """Mean position of the kilns in ``frame`` (display/search centre)."""
    lat = pd.to_numeric(frame["lat"], errors="coerce")
    lon = pd.to_numeric(frame["lon"], errors="coerce")
    return float(lat.mean()), float(lon.mean())


def place_key(kind: str, district: str, name: str = "") -> str:
    """Stable string key for a place (used as the selectbox option)."""
    return f"{kind}|{district}|{name}"


def build_places(
    frame: pd.DataFrame,
    *,
    label_fmt: str = "{name} · {count}",
    district_name: Callable[[str], str] = lambda value: value,
) -> list[Place]:
    """List every origin the data can answer for, with kiln counts.

    Input: prepared kiln frame. Output: districts first, then upazilas that
    have data, then known ``nearest_place`` names (grouped per district and
    centred on the kilns that reference them). ``label_fmt`` receives
    ``name`` and ``count``; ``district_name`` maps a raw district to its label.
    """
    needed = {"lat", "lon", "district"}
    if frame.empty or not needed.issubset(frame.columns):
        return []
    work = frame.assign(
        _district=frame["district"].map(_clean),
        _upazila=frame["upazila"].map(_clean) if "upazila" in frame.columns else "",
        _place=frame["nearest_place"].map(_clean) if "nearest_place" in frame.columns else "",
    )
    work = work[work["_district"] != ""]
    places: list[Place] = []
    for district, part in sorted(work.groupby("_district"), key=lambda item: item[0]):
        lat, lon = _centre(part)
        name = district_name(district)
        places.append(Place(
            place_key(KIND_DISTRICT, district), KIND_DISTRICT, name,
            label_fmt.format(name=name, count=len(part)), lat, lon, district, "", len(part),
        ))
    for (district, upazila), part in sorted(
        work[work["_upazila"] != ""].groupby(["_district", "_upazila"]), key=lambda item: item[0]
    ):
        lat, lon = _centre(part)
        name = f"{upazila}, {district_name(district)}"
        places.append(Place(
            place_key(KIND_UPAZILA, district, upazila), KIND_UPAZILA, upazila,
            label_fmt.format(name=name, count=len(part)), lat, lon, district, upazila, len(part),
        ))
    named = work[work["_place"] != ""]
    for (district, place), part in sorted(
        named.groupby(["_district", "_place"]), key=lambda item: item[0]
    ):
        lat, lon = _centre(part)
        name = f"{place}, {district_name(district)}"
        places.append(Place(
            place_key(KIND_NAMED, district, place), KIND_NAMED, place,
            label_fmt.format(name=name, count=len(part)), lat, lon, district, "", len(part),
        ))
    return places


#: Named in the brief as the demo example; used only when the data has this upazila.
EXAMPLE_DISTRICT = "Dhaka"
EXAMPLE_UPAZILA = "Savar"


def example_origin(places: Sequence[Place]) -> Place | None:
    """Pick the "Try an example" origin: Savar (Dhaka) if present, else the busiest upazila.

    Input: places from ``build_places``. Output: a ``KIND_POINT`` place at the
    upazila's kiln centre (data-derived, no typed coordinates), or ``None`` when
    the data has no upazila. Searched with ``DEFAULT_RADIUS_M``.
    """
    upazilas = [item for item in places if item.kind == KIND_UPAZILA]
    if not upazilas:
        return None
    chosen = next(
        (item for item in upazilas if item.upazila == EXAMPLE_UPAZILA and item.district == EXAMPLE_DISTRICT),
        None,
    ) or max(upazilas, key=lambda item: (item.kiln_count, item.key))
    return point_place(f"{chosen.upazila}, {chosen.district}", chosen.lat, chosen.lon)


def point_place(name: str, lat: float, lon: float) -> Place:
    """Build an ad-hoc origin for a geocoded name or a GPS fix."""
    return Place(
        place_key(KIND_POINT, "", f"{lat:.5f},{lon:.5f}"), KIND_POINT, name, name,
        float(lat), float(lon),
    )


# --------------------------------------------------------------------------
# Search
# --------------------------------------------------------------------------
def _distances(frame: pd.DataFrame, lat: float, lon: float) -> np.ndarray:
    """Metre distances from every kiln to (lat, lon), projected CRS."""
    return kd.distances_from_point_m(
        pd.to_numeric(frame["lat"], errors="coerce").to_numpy(dtype="float64", na_value=np.nan),
        pd.to_numeric(frame["lon"], errors="coerce").to_numpy(dtype="float64", na_value=np.nan),
        lat, lon,
    )


def _area_rows(frame: pd.DataFrame, place: Place) -> pd.DataFrame:
    """Rows of a whole-area choice (district or upazila)."""
    mask = frame["district"].map(_clean).eq(place.district)
    if place.kind == KIND_UPAZILA:
        mask &= frame["upazila"].map(_clean).eq(place.upazila)
    return frame[mask]


def search(frame: pd.DataFrame, place: Place, radius_m: int | None) -> SearchResult:
    """Find the kilns for ``place``.

    Whole areas (district/upazila) return every kiln in the area and ignore
    ``radius_m``. Named places and points return kilns within ``radius_m``
    metres (all districts considered). Rows are copies sorted by distance.
    """
    if place.radius_applies:
        radius = int(radius_m if radius_m is not None else DEFAULT_RADIUS_M)
        rows = frame
        used_radius: int | None = radius
    else:
        rows = _area_rows(frame, place)
        used_radius = None
    distances = _distances(rows, place.lat, place.lon) if len(rows) else np.empty(0)
    rows = rows.copy()
    rows["distance_m"] = distances
    if used_radius is not None:
        rows = rows[rows["distance_m"] <= used_radius]
    rows = rows.sort_values("distance_m", kind="stable")
    summary = kd.priority_summary(rows) if "priority_band" in rows.columns else {"total": int(len(rows))}
    return SearchResult(place, rows, used_radius, summary)


def nearest_beyond(frame: pd.DataFrame, lat: float, lon: float) -> tuple[float, pd.Series] | None:
    """Return ``(distance_m, row)`` of the kiln closest to a point, or None."""
    if frame.empty:
        return None
    distances = _distances(frame, lat, lon)
    if not np.isfinite(distances).any():
        return None
    position = int(np.argmin(distances))
    return float(distances[position]), frame.iloc[position]


def next_radius(radius_m: int, choices: Sequence[int] = RADIUS_CHOICES_M) -> int | None:
    """Smallest choice larger than ``radius_m``, or None at the maximum."""
    larger = [value for value in choices if value > radius_m]
    return min(larger) if larger else None


def radius_to_reach(distance_m: float, choices: Sequence[int] = RADIUS_CHOICES_M) -> int | None:
    """Smallest radius choice (metres) that reaches ``distance_m``, or None."""
    reaching = [value for value in choices if value >= distance_m]
    return min(reaching) if reaching else None


def covered_district(
    frame: pd.DataFrame, lat: float, lon: float, margin_m: float = COVERAGE_MARGIN_M
) -> str | None:
    """Name the covered district whose kiln bounding box (+ margin) holds the point.

    Heuristic: the data has no district polygons, so a district "covers" a
    point when it lies in the lat/lon box of that district's kilns widened by
    ``margin_m``. Returns None when no district does (point outside coverage).
    """
    if frame.empty or "district" not in frame.columns:
        return None
    d_lat = margin_m / 110_574.0
    d_lon = margin_m / (111_320.0 * max(float(np.cos(np.radians(lat))), 0.01))
    best: tuple[float, str] | None = None
    for district, part in frame.groupby(frame["district"].map(_clean)):
        if not district:
            continue
        la = pd.to_numeric(part["lat"], errors="coerce")
        lo = pd.to_numeric(part["lon"], errors="coerce")
        if la.isna().all() or lo.isna().all():
            continue
        if la.min() - d_lat <= lat <= la.max() + d_lat and lo.min() - d_lon <= lon <= lo.max() + d_lon:
            gap = float(np.hypot(lat - la.mean(), lon - lo.mean()))
            if best is None or gap < best[0]:
                best = (gap, str(district))
    return best[1] if best else None


# --------------------------------------------------------------------------
# Geocoding fallback (optional)
# --------------------------------------------------------------------------
class GeocodeUnavailable(RuntimeError):
    """Raised when every provider failed to answer (network/timeout/limit)."""


Provider = Callable[[str], "tuple[float, float] | None"]

_RATE_LOCK = threading.Lock()
_LAST_CALL = [0.0]
MIN_INTERVAL_S = 1.1  # Nominatim usage policy: at most one request per second


def in_bangladesh(lat: float, lon: float) -> bool:
    """True when the point lies inside the coarse Bangladesh bounding box."""
    lat_min, lat_max, lon_min, lon_max = BANGLADESH_BBOX
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def _wait_turn(
    clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep
) -> None:
    """Block until at least ``MIN_INTERVAL_S`` has passed since the last call."""
    with _RATE_LOCK:
        gap = MIN_INTERVAL_S - (clock() - _LAST_CALL[0])
        if gap > 0:
            sleep(gap)
        _LAST_CALL[0] = clock()


def default_providers(timeout_s: int = 8) -> list[Provider]:
    """Nominatim (restricted to BD) then Photon, each with a short timeout."""

    def nominatim(query: str) -> tuple[float, float] | None:
        from geopy.geocoders import Nominatim

        hit = Nominatim(user_agent="dhoa-bd-community", timeout=timeout_s).geocode(
            query, country_codes="bd"
        )
        return (float(hit.latitude), float(hit.longitude)) if hit else None

    def photon(query: str) -> tuple[float, float] | None:
        from geopy.geocoders import Photon

        hit = Photon(user_agent="dhoa-bd-community", timeout=timeout_s).geocode(query)
        return (float(hit.latitude), float(hit.longitude)) if hit else None

    return [nominatim, photon]


def geocode_bangladesh(
    query: str,
    providers: Sequence[Provider] | None = None,
    *,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[float, float] | None:
    """Resolve a place name to a Bangladesh (lat, lon).

    Returns None when providers answered but nothing is in Bangladesh (safe to
    cache). Raises ``GeocodeUnavailable`` when no provider answered at all
    (must not be cached). Calls are rate-limited process-wide.
    """
    text = " ".join(query.split())
    if not text:
        return None
    answered = False
    for provider in providers if providers is not None else default_providers():
        _wait_turn(clock, sleep)
        try:
            hit: Any = provider(f"{text}, Bangladesh")
        except Exception:  # noqa: BLE001 - any transport/library error
            continue
        answered = True
        if hit is not None and in_bangladesh(float(hit[0]), float(hit[1])):
            return float(hit[0]), float(hit[1])
    if not answered:
        raise GeocodeUnavailable(text)
    return None
