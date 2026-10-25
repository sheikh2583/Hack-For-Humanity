"""P9: behaviour of the priority-list iframe component in real Chromium (no Streamlit needed).

The component is plain HTML/JS, so these tests load ``index.html`` directly and post the same
``streamlit:render`` message Streamlit sends. They are skipped when Playwright or its Chromium is not
installed. Why this exists: laying out all 2,135 rows at once cost ~0.55 s per render on a desktop CPU
(``tools/bench_list_component.py``), so only the first rows are rendered and the rest are appended on
demand; the tests pin that nothing else changed (every row stays reachable, selection and the
click-to-toggle still work, repeat renders keep the existing nodes).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "app" / "components" / "priority_candidate_list" / "index.html"
TOTAL = 700
COLUMNS = ["View", "Area", "Priority", "School", "Hospital"]


def _args(selected: str | None = None, total: int = TOTAL, tag: str = "a") -> dict[str, Any]:
    return {
        "columns": COLUMNS,
        "rows": [["View kiln", f"📍 {tag}{i}, Dhaka", "▲ High", "1.2 km", "500 m"] for i in range(total)],
        "kiln_ids": [f"k{i}" for i in range(total)],
        "select_label": "View kiln", "selected_label": "Selected", "aria_label": "Priority list",
        "aria_select_fmt": "{0}: {1}", "lang": "en", "height": 640, "selected_id": selected,
    }


@contextmanager
def _page() -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as error:  # noqa: BLE001 - no browser binary in this environment
            pytest.skip(f"Chromium not available: {error}")
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(COMPONENT.as_uri())
        page.evaluate(
            "window.__sent = []; window.addEventListener('message', e => {"
            " if (e.data && e.data.type === 'streamlit:setComponentValue') window.__sent.push(e.data.value); });"
        )
        try:
            yield page
        finally:
            browser.close()


_RENDER = "async (a) => { window.postMessage({ type: 'streamlit:render', args: a }, '*');" \
          " await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); }"


def _rendered(page: Any) -> int:
    return page.evaluate("document.querySelectorAll('#rows tr').length")


def test_first_render_lays_out_only_the_first_rows_but_reports_the_full_count() -> None:
    with _page() as page:
        page.evaluate(_RENDER, _args())
        assert _rendered(page) == 120
        assert page.get_attribute("#list-table", "aria-rowcount") == str(TOTAL + 1)
        assert page.get_attribute("#rows tr:last-child", "aria-rowindex") == "121"
        assert page.evaluate("document.querySelectorAll('#headers th[scope=col]').length") == len(COLUMNS)


def test_scrolling_reaches_every_row() -> None:
    with _page() as page:
        page.evaluate(_RENDER, _args())
        for _ in range(12):
            page.evaluate("document.getElementById('table-scroll').scrollTop = 1e9")
            page.wait_for_timeout(80)
            if _rendered(page) == TOTAL:
                break
        assert _rendered(page) == TOTAL
        assert page.inner_text("#rows tr:last-child td:nth-child(2)") == f"📍 a{TOTAL - 1}, Dhaka"


def test_identical_render_keeps_the_same_nodes_and_scroll_position() -> None:
    with _page() as page:
        args = _args()
        page.evaluate(_RENDER, args)
        page.evaluate("document.querySelector('#rows tr').__mark = 1; document.getElementById('table-scroll').scrollTop = 300")
        page.wait_for_timeout(80)
        top = page.evaluate("document.getElementById('table-scroll').scrollTop")
        page.evaluate(_RENDER, args)
        assert page.evaluate("document.querySelector('#rows tr').__mark") == 1
        assert page.evaluate("document.getElementById('table-scroll').scrollTop") == top


def test_selection_change_flips_only_two_rows_in_place() -> None:
    with _page() as page:
        page.evaluate(_RENDER, _args())
        page.evaluate("document.querySelector('#rows tr').__mark = 1")
        page.evaluate(_RENDER, _args("k3"))
        assert page.evaluate("document.querySelectorAll('#rows tr.selected').length") == 1
        assert page.evaluate("document.querySelector('#rows tr.selected').dataset.kilnId") == "k3"
        assert page.inner_text("#rows tr.selected button") == "Selected"
        assert page.get_attribute("#rows tr.selected button", "aria-pressed") == "true"
        assert page.get_attribute("#rows tr.selected button", "aria-label") == "Selected: 📍 a3, Dhaka"
        page.evaluate(_RENDER, _args("k5"))
        assert page.evaluate("document.querySelector('#rows tr.selected').dataset.kilnId") == "k5"
        assert page.evaluate("document.querySelectorAll('#rows tr.selected').length") == 1
        assert page.inner_text("#rows tr[data-kiln-id=k3] button") == "View kiln"
        assert page.get_attribute("#rows tr[data-kiln-id=k3] button", "aria-pressed") == "false"
        assert page.evaluate("document.querySelector('#rows tr').__mark") == 1  # nothing was rebuilt
        page.evaluate(_RENDER, _args(None))
        assert page.evaluate("document.querySelectorAll('#rows tr.selected').length") == 0


def test_selected_row_beyond_the_first_block_is_marked_when_it_is_reached() -> None:
    with _page() as page:
        page.evaluate(_RENDER, _args("k650"))
        assert _rendered(page) == 120  # selecting a deep row does not force rendering up to it
        assert page.evaluate("document.querySelectorAll('#rows tr.selected').length") == 0
        for _ in range(12):
            page.evaluate("document.getElementById('table-scroll').scrollTop = 1e9")
            page.wait_for_timeout(80)
            if page.query_selector("#rows tr[data-kiln-id=k650]"):
                break
        assert page.evaluate("document.querySelector('#rows tr.selected').dataset.kilnId") == "k650"
        assert page.get_attribute("#rows tr[data-kiln-id=k650] button", "aria-pressed") == "true"
        page.evaluate(_RENDER, _args("k20"))  # moving the selection updates the rendered rows only
        assert page.evaluate("document.querySelector('#rows tr.selected').dataset.kilnId") == "k20"
        assert page.evaluate("document.querySelectorAll('#rows tr.selected').length") == 1


def _click_and_read(page: Any, selector: str) -> dict[str, Any]:
    """Click, wait for the component's postMessage to arrive, return the value it sent."""
    count = page.evaluate("window.__sent.length")
    page.click(selector)
    page.wait_for_function(f"window.__sent.length > {count}")
    return page.evaluate("window.__sent.at(-1)")


def test_clicks_report_the_row_and_toggle_after_an_in_place_update() -> None:
    with _page() as page:
        page.evaluate(_RENDER, _args())
        assert _click_and_read(page, "#rows tr[data-kiln-id=k2] button")["kiln_id"] == "k2"
        page.evaluate(_RENDER, _args("k2"))  # what Streamlit does after the click
        # clicking the selected row clears it (the handler must read the *current* state)
        assert _click_and_read(page, "#rows tr[data-kiln-id=k2] button")["kiln_id"] is None
        # a click on the row itself, not just on the button
        assert _click_and_read(page, "#rows tr[data-kiln-id=k4] td:nth-child(2)")["kiln_id"] == "k4"


def test_tabbing_towards_the_end_appends_more_rows() -> None:
    with _page() as page:
        page.evaluate(_RENDER, _args())
        assert _rendered(page) == 120
        page.focus("#rows tr[data-index='115'] button")
        assert _rendered(page) == 360


def test_new_rows_reset_to_the_first_block_at_the_top() -> None:
    with _page() as page:
        page.evaluate(_RENDER, _args())
        page.evaluate("document.getElementById('table-scroll').scrollTop = 1e9")
        page.wait_for_timeout(80)
        assert _rendered(page) > 120
        page.evaluate(_RENDER, _args(tag="b", total=300))
        assert _rendered(page) == 120
        assert page.evaluate("document.getElementById('table-scroll').scrollTop") == 0
        assert page.inner_text("#rows tr:first-child td:nth-child(2)") == "📍 b0, Dhaka"
        assert page.get_attribute("#list-table", "aria-rowcount") == "301"


def test_page_keeps_far_fewer_nodes_than_the_all_rows_version() -> None:
    with _page() as page:
        page.evaluate(_RENDER, _args(total=2135))
        assert page.evaluate("document.getElementsByTagName('*').length") < 2_000  # was 14,964
