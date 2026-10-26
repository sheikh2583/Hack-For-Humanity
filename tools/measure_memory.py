"""Measure the dashboard's resident memory on the real data (CPU only).

Usage: ``python tools/measure_memory.py``. Prints process RSS (MB) after
import, after loading/preparing the data, after building the base map, and
after a Community search. Compare the last number with the memory limit shown
in Streamlit Community Cloud's current documentation (limits change; the app
dashboard also shows live usage under "Manage app"). Needs ``psutil`` or, on
Linux/macOS, the standard ``resource`` module.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))


def rss_mb() -> float:
    """Current resident set size in MB (peak on platforms without psutil)."""
    try:
        import psutil

        return psutil.Process(os.getpid()).memory_info().rss / 1e6
    except ImportError:
        import resource

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return peak / (1e6 if sys.platform == "darwin" else 1e3)


def main() -> None:
    print(f"start: {rss_mb():.0f} MB")
    import app.community as cm
    import app.streamlit_app as dashboard

    print(f"after imports: {rss_mb():.0f} MB")
    frame = dashboard.get_prepared_data()
    if frame is None:
        raise SystemExit("data/processed/kilns_prioritised.parquet not found")
    print(f"after load + prepare ({len(frame):,} rows): {rss_mb():.0f} MB")
    cm.search(frame, cm.point_place("p", float(frame["lat"].mean()), float(frame["lon"].mean())), 10000)
    print(f"after community search: {rss_mb():.0f} MB")


if __name__ == "__main__":
    main()
