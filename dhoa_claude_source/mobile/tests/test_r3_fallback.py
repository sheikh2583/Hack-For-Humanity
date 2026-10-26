"""R3 fix: the built-in copies of the Map-screen texts must equal the catalogues."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "app"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _fallback() -> dict[str, dict[str, str]]:
    import ast

    tree = ast.parse((ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "_R3_FALLBACK_TEXT":
            return ast.literal_eval(node.value)
    raise AssertionError("_R3_FALLBACK_TEXT not found")


def test_fallback_texts_match_both_catalogues() -> None:
    bn = importlib.import_module("strings_bn")
    en = importlib.import_module("strings_en")
    copies = _fallback()
    assert copies
    for name, langs in copies.items():
        assert langs["bn"] == getattr(bn, name), name
        assert langs["en"] == getattr(en, name), name


def test_map_screen_uses_safe_text_for_new_strings() -> None:
    source = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
    assert "T.MAP_CLEAR_SEARCH" not in source
    assert "T.MAP_SEARCH_FILTERS_NOTE" not in source
