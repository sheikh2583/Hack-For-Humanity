"""Find stale or missing files after copying a zip into the repo.

Run from the repo root:  python tools/check_install.py
Checks that (1) every T.NAME used anywhere in app/*.py exists in BOTH string catalogues,
(2) required modules/files from recent modules are present, (3) config keys exist.
Prints what is missing and exits 1; prints OK and exits 0 otherwise.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "app/trust.py", "app/voice.py", "app/components/voice_guide/index.html", "app/styles.py", "app/static/favicon.png",
    "app/components/priority_candidate_list/index.html", "config/dashboard.yaml",
    "src/eval/pdf_kit.py", "src/eval/generate_community_report.py",
)


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    problems: list[str] = []
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            problems.append(f"missing file: {rel}")
    used: dict[str, set[str]] = {}
    for source in (ROOT / "app").glob("*.py"):
        if source.name.startswith("strings"):
            continue
        for name in re.findall(r"\bT\.([A-Z][A-Z0-9_]+)\b", source.read_text(encoding="utf-8")):
            used.setdefault(name, set()).add(source.name)
    facade = (ROOT / "app" / "strings.py").read_text(encoding="utf-8")
    for name in re.findall(r"(?m)^([A-Z][A-Z0-9_]+)\s*(?::[^=\n]+)?=", facade):
        used.pop(name, None)  # defined in strings.py itself, not in the catalogues
    for lang in ("en", "bn"):
        catalogue = _load(ROOT / "app" / f"strings_{lang}.py")
        for name in sorted(used):
            if not hasattr(catalogue, name):
                problems.append(f"strings_{lang}.py is missing {name} (used in {', '.join(sorted(used[name]))})")
    config = (ROOT / "config" / "dashboard.yaml")
    if config.is_file() and "hotline_verified" not in config.read_text(encoding="utf-8"):
        problems.append("config/dashboard.yaml is old (no contact/about keys)")
    if problems:
        print("\n".join(problems))
        print(f"\n{len(problems)} problem(s): copy the listed files from the latest zips, then restart Streamlit.")
        return 1
    print("OK: all files and strings the app uses are present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
