"""Write ``requirements.lock.txt`` with exact versions of the dashboard packages.

Run inside the virtual environment you verified (tests green, app checked).
Input: the installed distributions. Output: ``requirements.lock.txt`` with
``name==version`` for every package named in ``requirements.txt`` plus their
installed dependencies that Streamlit Cloud would otherwise float.
"""

from __future__ import annotations

import re
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _names(requirements: Path) -> list[str]:
    names = []
    for line in requirements.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line and not line.startswith(("-", "http")):
            names.append(re.split(r"[<>=!~\[; ]", line, maxsplit=1)[0])
    return names


def _closure(roots: list[str]) -> dict[str, str]:
    seen: dict[str, str] = {}
    stack = list(roots)
    while stack:
        name = stack.pop()
        key = name.lower().replace("_", "-")
        if key in seen:
            continue
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue
        seen[key] = dist.version
        for requirement in dist.requires or []:
            if "extra ==" in requirement:
                continue
            stack.append(re.split(r"[<>=!~\[; ]", requirement.strip(), maxsplit=1)[0])
    return seen


def main() -> None:
    pins = _closure(_names(ROOT / "requirements.txt"))
    lines = [f"{name}=={version}" for name, version in sorted(pins.items())]
    (ROOT / "requirements.lock.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote requirements.lock.txt ({len(lines)} packages)")


if __name__ == "__main__":
    main()
