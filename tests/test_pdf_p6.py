"""P6 checks: kiln and community PDFs in both languages, long names, pagination, label parity."""

from __future__ import annotations

import re

import pandas as pd
import pytest

from src.eval import pdf_kit
from src.eval.generate_community_report import generate_community_report
from src.eval.generate_report import generate_kiln_report

LONG_BN = "চট্টগ্রামের অন্তর্গত অত্যন্ত দীর্ঘ নামের একটি গ্রাম ও ইউনিয়ন পরিষদ এলাকা"
LONG_EN = "Extraordinarily Long Place Name Of A Village Union Parishad Area In Bangladesh"


def _rows(count: int) -> pd.DataFrame:
    return pd.DataFrame({
        "distance_m": [100.0 + 37 * i for i in range(count)],
        "class": ["FCBK" if i % 2 else "Zigzag" for i in range(count)],
        "priority_band": [("High", "Medium", "Low")[i % 3] for i in range(count)],
        "lat": [23.7 + i * 1e-3 for i in range(count)],
        "lon": [90.4 + i * 1e-3 for i in range(count)],
        "upazila": ["Savar"] * count,
        "district": ["Dhaka"] * count,
    })


def _pages(pdf: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf))


@pytest.mark.parametrize("lang", ["bn", "en"])
@pytest.mark.parametrize("place", [LONG_BN, LONG_EN, "Savar"])
def test_community_pdf_both_languages(lang: str, place: str) -> None:
    pdf = generate_community_report(place, _rows(5), 5000, lang)
    assert pdf is not None and pdf.startswith(b"%PDF")


@pytest.mark.parametrize("lang", ["bn", "en"])
def test_community_pdf_paginates(lang: str) -> None:
    small = generate_community_report("Savar", _rows(3), 5000, lang)
    big = generate_community_report("Savar", _rows(120), 5000, lang)
    assert small is not None and big is not None
    assert _pages(small) == 1
    assert _pages(big) > 1


@pytest.mark.parametrize("lang", ["bn", "en"])
def test_community_pdf_empty_and_whole_area(lang: str) -> None:
    assert generate_community_report("Savar", _rows(0), 0, lang) is not None
    assert generate_community_report("Savar", _rows(4), 0, lang) is not None


@pytest.mark.parametrize("lang", ["bn", "en"])
def test_kiln_pdf_long_names(lang: str) -> None:
    for place in (LONG_BN, LONG_EN):
        pdf = generate_kiln_report(
            {"kiln_id": "k1", "district": "Dhaka", "upazila": "Savar", "class": "FCBK", "priority_band": "High",
             "lat": 23.7, "lon": 90.4, "nearest_place": place, "dist_schools_m": 90.0}, lang
        )
        assert pdf is not None and _pages(pdf) == 1


def test_labels_key_parity() -> None:
    assert set(pdf_kit.LABELS["bn"]) == set(pdf_kit.LABELS["en"])
    for key in ("near_in", "in_area"):
        fields = {lang: set(re.findall(r"{(\w+)", pdf_kit.LABELS[lang][key])) for lang in ("bn", "en")}
        assert fields["bn"] == fields["en"]
