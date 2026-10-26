"""Measure why the dashboard feels slow: real browser, in-process Streamlit run, and hot paths.

Three modes (run them in this order; paste the output into ``docs/HANDOFF_P9.md``):

``browser URL``   Chromium (Playwright) against a RUNNING app, e.g. ``http://localhost:8501``.
                  For each scenario a fresh browser context (empty HTTP cache) records: time to the
                  skeleton / title / hero, time until the app is *settled* (no request in flight and no
                  WebSocket frame for ``--quiet`` ms), time until the map is interactive (a loaded tile
                  and a marker) and the list is drawn, bytes by resource type, WebSocket bytes and the
                  largest frames, basemap-tile statuses and failures, the slowest requests and main-thread
                  long tasks (>50 ms). Scenarios: cold visit, each ``--nav`` label, selecting the first
                  list row, plus any ``--click`` labels (e.g. the filter Apply button).
                  Use ``--cpu 4`` and ``--network slow4g`` to approximate a mid-range phone.
``apptest``       Runs ``app/streamlit_app.py`` through ``streamlit.testing.v1.AppTest`` so the code runs
                  inside a script-run context (``tools/benchmark_dashboard.py`` does not: language lookups
                  take a shortcut there). Prints cold and warm run times per view and, with ``--profile``,
                  the heaviest functions. Needs the real parquet (or ``DHOA_DATA_DIR``).
``stages``        Times ``get_prepared_data``, ``load_config``, the data-date lookup, ``marker_payload``,
                  the list payload (and its JSON size) and ``page_css`` on the real parquet.

Nothing here changes the app. Ground rule 6 concerns GPU work only; this is CPU/browser timing.
"""

from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TILE_HINTS = ("tile.openstreetmap.org", "arcgisonline.com")
LONGTASK_INIT = """
(() => { window.__longtasks = [];
  try { new PerformanceObserver(list => { for (const e of list.getEntries())
    window.__longtasks.push(Math.round(e.duration)); }).observe({ type: 'longtask', buffered: true }); } catch (e) {} })();
"""
NETWORK = {  # latency ms, down bytes/s, up bytes/s  (Lighthouse-style presets)
    "slow4g": (150, int(1.6 * 1024 * 1024 / 8), int(750 * 1024 / 8)),
    "fast3g": (562, int(1.6 * 1024 * 1024 / 8), int(750 * 1024 / 8)),
}


# --------------------------------------------------------------------------- browser mode
class Recorder:
    """Collects requests, WebSocket frames and timings for one page."""

    def __init__(self, page: Any) -> None:
        self.started: dict[Any, float] = {}
        self.records: list[dict[str, Any]] = []
        self.in_flight = 0
        self.ws_bytes = 0
        self.ws_frames: list[int] = []
        self.last_activity = time.perf_counter()
        page.on("request", self._request)
        page.on("requestfinished", self._finished)
        page.on("requestfailed", self._failed)
        page.on("websocket", self._websocket)

    def _touch(self) -> None:
        self.last_activity = time.perf_counter()

    def _request(self, request: Any) -> None:
        self.started[request] = time.perf_counter()
        self.in_flight += 1
        self._touch()

    def _finished(self, request: Any) -> None:
        self.in_flight = max(0, self.in_flight - 1)
        self._touch()
        try:
            response = request.response()
            status = response.status if response else None
            sizes = request.sizes()
            size = int(sizes.get("responseBodySize", 0)) + int(sizes.get("responseHeadersSize", 0))
        except Exception:  # noqa: BLE001 - sizes are best effort
            status, size = None, 0
        self.records.append(self._row(request, status, size, None))

    def _failed(self, request: Any) -> None:
        self.in_flight = max(0, self.in_flight - 1)
        self._touch()
        self.records.append(self._row(request, None, 0, request.failure))

    def _row(self, request: Any, status: int | None, size: int, failure: str | None) -> dict[str, Any]:
        url = request.url
        return {
            "url": url, "type": request.resource_type, "status": status, "bytes": size, "failure": failure,
            "ms": round((time.perf_counter() - self.started.get(request, time.perf_counter())) * 1000),
            "tile": any(hint in url for hint in TILE_HINTS),
        }

    def _websocket(self, ws: Any) -> None:
        def frame(payload: Any) -> None:
            size = len(payload)
            self.ws_bytes += size
            self.ws_frames.append(size)
            self._touch()

        ws.on("framereceived", frame)

    def mark(self) -> tuple[int, int, int]:
        return len(self.records), self.ws_bytes, len(self.ws_frames)

    def settle(self, page: Any, quiet_ms: int, timeout_s: float = 90.0) -> float:
        """Wait until nothing is in flight and nothing arrived for ``quiet_ms``; return seconds waited."""
        start = time.perf_counter()
        while time.perf_counter() - start < timeout_s:
            idle_ms = (time.perf_counter() - self.last_activity) * 1000
            if self.in_flight == 0 and idle_ms >= quiet_ms:
                return time.perf_counter() - start - quiet_ms / 1000
            page.wait_for_timeout(40)
        return float("nan")


def _longtasks(page: Any) -> list[int]:
    values: list[int] = []
    for frame in page.frames:
        try:
            values += frame.evaluate("window.__longtasks || []")
        except Exception:  # noqa: BLE001 - frame may be detached
            continue
    return values


def _watch(page: Any, scripts: dict[str, str], started: float, timeout_s: float, need: tuple[str, ...]) -> dict[str, float | None]:
    """Seconds from ``started`` at which each script first became truthy in any frame (None if never).

    Stops when every name in ``need`` has been seen or after ``timeout_s``.
    """
    seen: dict[str, float | None] = {name: None for name in scripts}
    while time.perf_counter() - started < timeout_s and any(seen[name] is None for name in need):
        for name, script in scripts.items():
            if seen[name] is not None:
                continue
            for frame in page.frames:
                try:
                    if frame.evaluate(script):
                        seen[name] = round(time.perf_counter() - started, 2)
                        break
                except Exception:  # noqa: BLE001 - frame may be navigating or detached
                    continue
        page.wait_for_timeout(40)
    return seen


MAP_READY = "document.querySelectorAll('.leaflet-tile-loaded').length > 0 && document.querySelectorAll('.leaflet-marker-icon, .marker-cluster').length > 0"
LIST_READY = "document.querySelectorAll('#rows tr').length > 0"


def _click_label(page: Any, label: str) -> None:
    for role in ("button", "radio", "tab"):
        locator = page.get_by_role(role, name=label)
        if locator.count():
            locator.first.click()
            return
    page.get_by_text(label, exact=True).first.click()


def _summary(recorder: Recorder, before: tuple[int, int, int], longtasks_before: int, page: Any) -> dict[str, Any]:
    records = recorder.records[before[0]:]
    by_type: dict[str, int] = collections.Counter()
    for row in records:
        by_type[row["type"]] += row["bytes"]
    tiles = [row for row in records if row["tile"]]
    ws_frames = recorder.ws_frames[before[2]:]
    longs = _longtasks(page)[longtasks_before:]
    return {
        "requests": len(records),
        "http_kb": round(sum(row["bytes"] for row in records) / 1024, 1),
        "http_kb_by_type": {key: round(value / 1024, 1) for key, value in sorted(by_type.items(), key=lambda kv: -kv[1])},
        "ws_kb": round((recorder.ws_bytes - before[1]) / 1024, 1),
        "ws_largest_kb": sorted((round(size / 1024, 1) for size in ws_frames), reverse=True)[:5],
        "tiles": len(tiles),
        "tile_status": dict(collections.Counter(str(row["status"] or row["failure"]) for row in tiles)),
        "tile_median_ms": round(statistics.median([row["ms"] for row in tiles])) if tiles else None,
        "tile_max_ms": max((row["ms"] for row in tiles), default=None),
        "slowest": [
            {"ms": row["ms"], "status": row["status"] or row["failure"], "kb": round(row["bytes"] / 1024, 1), "url": row["url"][:110]}
            for row in sorted(records, key=lambda r: -r["ms"])[:6]
        ],
        "longtasks": len(longs), "longtask_ms_total": sum(longs), "longtask_ms_max": max(longs, default=0),
    }


def run_browser(args: argparse.Namespace) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    url = args.url + ("&" if "?" in args.url else "?") + f"lang={args.lang}" if args.lang else args.url
    out: dict[str, Any] = {"url": url, "cpu": args.cpu, "network": args.network, "scenarios": {}}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": args.width, "height": 900})
        context.add_init_script(LONGTASK_INIT)
        page = context.new_page()
        client = context.new_cdp_session(page)
        if args.cpu > 1:
            client.send("Emulation.setCPUThrottlingRate", {"rate": args.cpu})
        if args.network in NETWORK:
            latency, down, up = NETWORK[args.network]
            client.send("Network.enable")
            client.send("Network.emulateNetworkConditions", {"offline": False, "latency": latency, "downloadThroughput": down, "uploadThroughput": up})
        recorder = Recorder(page)

        # 1. cold visit (the Streamlit server may be warm; the browser cache is empty)
        before, long_before, t0 = recorder.mark(), 0, time.perf_counter()
        page.goto(url, wait_until="commit")
        marks = _watch(
            page,
            {"skeleton_s": "!!document.querySelector('.dhoa-skeleton')", "title_s": "!!document.querySelector('.dhoa-brand-title')",
             "hero_s": "!!document.querySelector('.dhoa-hero')"},
            t0, 120, need=("title_s", "hero_s"),
        )
        recorder.settle(page, args.quiet)
        settled_after = max(0.0, time.perf_counter() - t0 - args.quiet / 1000)
        paint = page.evaluate("performance.getEntriesByName('first-contentful-paint').map(e => Math.round(e.startTime))")
        scenario = _summary(recorder, before, long_before, page)
        scenario.update({"first_contentful_paint_ms": paint[0] if paint else None, "settled_after_s": round(settled_after, 2), **marks})
        out["scenarios"]["cold visit"] = scenario

        # 2. every view, clicked in turn
        for label in [item.strip() for item in args.nav.split(",") if item.strip()]:
            before, long_before, t0 = recorder.mark(), len(_longtasks(page)), time.perf_counter()
            _click_label(page, label)
            extra: dict[str, float | None] = {}
            if label == args.map_label:
                extra = _watch(page, {"map_interactive_s": MAP_READY, "list_drawn_s": LIST_READY}, t0, 90, need=("map_interactive_s", "list_drawn_s"))
            recorder.settle(page, args.quiet)
            result = _summary(recorder, before, long_before, page)
            result["settled_after_s"] = round(max(0.0, time.perf_counter() - t0 - args.quiet / 1000), 2)
            result.update(extra)
            out["scenarios"][f"open {label}"] = result

        # 3. select the first row of the priority list (a fragment rerun), then optional labelled clicks
        actions: list[tuple[str, Any]] = []
        if any(frame.evaluate("!!document.querySelector('#rows button')") for frame in page.frames if _safe(frame)):
            actions.append(("select first list row", lambda: _click_in_frames(page, "#rows tr button")))
        actions += [(f"click '{label}'", (lambda lab=label: _click_label(page, lab))) for label in args.click]
        for name, action in actions:
            before, long_before, t0 = recorder.mark(), len(_longtasks(page)), time.perf_counter()
            action()
            recorder.settle(page, args.quiet)
            result = _summary(recorder, before, long_before, page)
            result["settled_after_s"] = round(max(0.0, time.perf_counter() - t0 - args.quiet / 1000), 2)
            out["scenarios"][name] = result
        browser.close()
    return out


def _safe(frame: Any) -> bool:
    try:
        frame.evaluate("1")
        return True
    except Exception:  # noqa: BLE001
        return False


def _click_in_frames(page: Any, selector: str) -> None:
    for frame in page.frames:
        if _safe(frame) and frame.query_selector(selector):
            frame.locator(selector).first.click()
            return


def print_browser(result: dict[str, Any]) -> None:
    print(f"\nURL {result['url']}  cpu x{result['cpu']}  network {result['network'] or 'unthrottled'}\n")
    print("| scenario | settled s | map interactive s | list drawn s | requests | HTTP KB | WS KB | tiles (status) | long tasks (n / total ms / max ms) |")
    print("|---|---|---|---|---|---|---|---|---|")
    for name, row in result["scenarios"].items():
        print(
            f"| {name} | {row.get('settled_after_s')} | {row.get('map_interactive_s', '')} | {row.get('list_drawn_s', '')} | "
            f"{row['requests']} | {row['http_kb']} | {row['ws_kb']} | {row['tiles']} {row['tile_status'] or ''} | "
            f"{row['longtasks']} / {row['longtask_ms_total']} / {row['longtask_ms_max']} |"
        )
    cold = result["scenarios"].get("cold visit", {})
    print(f"\ncold visit: first contentful paint {cold.get('first_contentful_paint_ms')} ms, skeleton {cold.get('skeleton_s')} s, "
          f"title {cold.get('title_s')} s, hero {cold.get('hero_s')} s")
    print(f"HTTP KB by type (cold): {cold.get('http_kb_by_type')}")
    for name, row in result["scenarios"].items():
        print(f"\nslowest requests, {name} (largest WS frames KB: {row['ws_largest_kb']}; tile median/max ms: {row['tile_median_ms']}/{row['tile_max_ms']})")
        for item in row["slowest"]:
            print(f"  {item['ms']:>6} ms  {str(item['status']):>8}  {item['kb']:>8} KB  {item['url']}")


# --------------------------------------------------------------------------- apptest mode
def run_apptest(args: argparse.Namespace) -> None:
    import cProfile
    import pstats

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "app"))
    from streamlit.testing.v1 import AppTest

    script = str(ROOT / "app" / "streamlit_app.py")
    rows: list[tuple[str, float]] = []
    profile = cProfile.Profile() if args.profile else None
    at = AppTest.from_file(script, default_timeout=args.timeout)
    at.session_state["dhoa_lang"] = args.lang or "bn"
    if profile:
        profile.enable()
    start = time.perf_counter()
    at.run()
    rows.append(("first run (imports + data load + Overview)", time.perf_counter() - start))
    if profile:
        profile.disable()
    for _ in range(args.repeat):
        start = time.perf_counter()
        at.run()
        rows.append(("warm rerun, Overview", time.perf_counter() - start))
    for view in ("inspector", "community", "about", "overview"):
        at.session_state["dhoa_view_mode"] = view
        start = time.perf_counter()
        at.run()
        rows.append((f"first run of view '{view}'", time.perf_counter() - start))
        start = time.perf_counter()
        at.run()
        rows.append((f"warm rerun of view '{view}'", time.perf_counter() - start))
    print("| step | seconds |\n|---|---|")
    for name, seconds in rows:
        print(f"| {name} | {seconds:.2f} |")
    print(f"\nexceptions after last run: {len(at.exception)}")
    if profile:
        print("\nheaviest functions of the first run (cumulative):")
        pstats.Stats(profile).sort_stats("cumulative").print_stats(args.top)


# --------------------------------------------------------------------------- stages mode
def run_stages(args: argparse.Namespace) -> None:
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "app"))
    import app.kiln_data as kd
    import app.streamlit_app as dashboard
    import app.styles as styles
    import app.strings as T

    def timed(label: str, fn: Any, repeat: int = 3) -> Any:
        best, result = float("inf"), None
        for _ in range(repeat):
            start = time.perf_counter()
            result = fn()
            best = min(best, time.perf_counter() - start)
        print(f"| {label} | {best:.3f} |")
        return result

    print("| step (best of 3, outside a script-run context) | seconds |\n|---|---|")
    start = time.perf_counter()
    frame = dashboard.get_prepared_data()
    print(f"| get_prepared_data (first call: parquet read + prepare) | {time.perf_counter() - start:.3f} |")
    if frame is None:
        raise SystemExit("data/processed/kilns_prioritised.parquet not found")
    timed("get_prepared_data (cached)", dashboard.get_prepared_data)
    timed("load_config (cached)", dashboard.load_config)
    timed("dashboard_kilns_file + _data_date_label (stat calls)", lambda: dashboard._data_date_label(dashboard.dashboard_kilns_file()))
    rules = dashboard._siting_rules()
    payload = timed("kd.marker_payload", lambda: kd.marker_payload(frame, rules))
    listing = timed("kd.build_list_frame + astype(str).values.tolist()", lambda: kd.build_list_frame(frame, rules).astype(str).values.tolist())
    timed("styles.page_css", lambda: styles.page_css(T.PAGE_LOADING))
    print(f"\nrows {len(frame):,}; marker payload {len(json.dumps(payload, ensure_ascii=False)) / 1024:.0f} KB; "
          f"list payload {len(json.dumps(listing, ensure_ascii=False)) / 1024:.0f} KB; page_css {len(styles.page_css(T.PAGE_LOADING).encode()) / 1024:.0f} KB")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)
    b = sub.add_parser("browser")
    b.add_argument("url")
    b.add_argument("--nav", default="", help="comma-separated visible nav labels, e.g. 'Overview,Map,Near me,About'")
    b.add_argument("--map-label", default="Map", help="which --nav label opens the map (adds map-interactive timing)")
    b.add_argument("--lang", default="", help="bn or en (sets ?lang=)")
    b.add_argument("--click", action="append", default=[], help="extra button label to click and time (repeatable)")
    b.add_argument("--cpu", type=int, default=1)
    b.add_argument("--network", default="", choices=["", *NETWORK])
    b.add_argument("--width", type=int, default=1280)
    b.add_argument("--quiet", type=int, default=800, help="ms of silence that count as settled")
    b.add_argument("--out", default="")
    a = sub.add_parser("apptest")
    a.add_argument("--lang", default="")
    a.add_argument("--repeat", type=int, default=2)
    a.add_argument("--profile", action="store_true")
    a.add_argument("--top", type=int, default=25)
    a.add_argument("--timeout", type=int, default=180)
    sub.add_parser("stages")
    args = parser.parse_args()
    if args.mode == "browser":
        result = run_browser(args)
        print_browser(result)
        if args.out:
            Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    elif args.mode == "apptest":
        run_apptest(args)
    else:
        run_stages(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
