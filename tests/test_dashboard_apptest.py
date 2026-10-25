"""Streamlit AppTest smoke tests: both views load without exceptions, Bangla-only."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py")


def _all_text(at: AppTest) -> str:
    parts: list[str] = []
    for collection in (at.markdown, at.caption, at.subheader, at.title, at.button, at.toggle, at.selectbox):
        parts.extend(str(getattr(item, "value", "")) + str(getattr(item, "label", "")) for item in collection)
    return "\n".join(parts)


@pytest.mark.parametrize("view", ["inspector", "community"])
def test_view_loads_without_exception_and_has_no_language_toggle(view: str) -> None:
    """Each view runs end-to-end on the real data with no exception and no English toggle."""
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["dhoa_view_mode"] = view
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.toggle, [t.label for t in at.toggle]
    assert "English / বাংলা" not in _all_text(at)
