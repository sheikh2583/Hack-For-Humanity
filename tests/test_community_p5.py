"""P5 tests: community search suggestions and matching localized copy.

Input: a tiny synthetic frame. Output: case-insensitive, prefix-ranked area suggestions.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pandas as pd

import app.community as cm
import app.streamlit_app as dashboard

ROOT = Path(__file__).resolve().parent.parent
NEW = ("C_PLACE_SUGGESTIONS", "C_PLACE_SUGGESTION_PLACEHOLDER")


def _frame(rows: list[tuple[str, str, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["district", "upazila", "lat", "lon"])


def test_example_prefers_savar_in_dhaka_and_uses_data_centre() -> None:
    frame = _frame([("Dhaka", "Savar", 23.8, 90.2), ("Dhaka", "Savar", 23.9, 90.4),
                    ("Gazipur", "Tongi", 24.0, 90.4), ("Gazipur", "Tongi", 24.0, 90.5),
                    ("Gazipur", "Tongi", 24.1, 90.5)])
    origin = cm.example_origin(cm.build_places(frame))
    assert origin is not None and origin.kind == cm.KIND_POINT and origin.radius_applies
    assert origin.name == "Savar, Dhaka"
    assert abs(origin.lat - 23.85) < 1e-9 and abs(origin.lon - 90.3) < 1e-9


def test_example_falls_back_to_busiest_upazila_and_handles_no_upazila() -> None:
    frame = _frame([("Gazipur", "Tongi", 24.0, 90.4), ("Gazipur", "Tongi", 24.1, 90.5),
                    ("Rajshahi", "Paba", 24.4, 88.6)])
    assert cm.example_origin(cm.build_places(frame)).name == "Tongi, Gazipur"
    assert cm.example_origin([]) is None


def test_example_uses_the_default_five_km_radius() -> None:
    assert cm.DEFAULT_RADIUS_M == 5000 and 5000 in cm.RADIUS_CHOICES_M


def test_strings_in_both_languages_with_matching_fields() -> None:
    def load(name: str) -> dict[str, str]:
        tree = ast.parse((ROOT / "app" / name).read_text(encoding="utf-8"))
        return {n.targets[0].id: n.value.value for n in tree.body
                if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)}
    bn, en = load("strings_bn.py"), load("strings_en.py")
    for name in NEW:
        assert name in bn and name in en
        assert re.findall(r"\{[^}]*\}", bn[name]) == re.findall(r"\{[^}]*\}", en[name])


def test_typed_area_suggestions_are_case_insensitive_and_prefix_ranked() -> None:
    frame = pd.DataFrame([
        ("Gazipur", "Tongi", "Tongi Bazaar", 24.0, 90.4),
        ("Gazipur", "Tongi", "Tongi Bazaar", 24.1, 90.5),
        ("Dhaka", "Savar", "Tongi Road", 23.8, 90.2),
    ], columns=["district", "upazila", "nearest_place", "lat", "lon"])
    places = {place.key: place for place in cm.build_places(frame)}

    suggestions = dashboard._community_place_suggestions(places, "tOn")

    assert suggestions
    assert all("ton" in places[key].name.casefold()
               or "ton" in places[key].district.casefold()
               or "ton" in places[key].upazila.casefold()
               or "ton" in places[key].label.casefold() for key in suggestions)
    assert places[suggestions[0]].name.casefold().startswith("ton")
    assert dashboard._community_place_suggestions(places, " ") == []
