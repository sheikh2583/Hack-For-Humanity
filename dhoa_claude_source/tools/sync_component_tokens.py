"""Rewrite the generated ``:root`` token block inside the static iframe components.

Usage: ``python tools/sync_component_tokens.py`` (add ``--check`` to only verify).
Input: ``app/components/*/index.html`` containing the dhoa-tokens start/end markers.
Output: those files with the block replaced by ``design_tokens.component_root_block()``.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import design_tokens as tk  # noqa: E402


def sync(path: Path, check: bool = False) -> bool:
    """Return True when ``path`` already matches (and rewrite it unless ``check``)."""
    text = path.read_text(encoding="utf-8")
    start, end = text.find("/* dhoa-tokens:start"), text.find(tk.COMPONENT_BLOCK_END)
    if start < 0 or end < 0:
        raise SystemExit(f"{path}: token markers missing")
    line_start = text.rfind("\n", 0, start) + 1
    new = text[:line_start] + tk.component_root_block() + text[end + len(tk.COMPONENT_BLOCK_END):]
    if new == text:
        return True
    if not check:
        path.write_text(new, encoding="utf-8")
    return False


if __name__ == "__main__":
    ok = True
    for html in sorted((ROOT / "app" / "components").glob("*/index.html")):
        ok &= sync(html, check="--check" in sys.argv)
    raise SystemExit(0 if ok else 1)
