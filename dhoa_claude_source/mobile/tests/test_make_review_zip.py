"""Tests for deterministic and safe Claude review ZIP generation."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

from scripts.make_review_zip import INCLUDE_PATHS, REQUIRED_ENTRIES, make_review_zip


def _make_minimal_project(root: Path) -> None:
    """Create the smallest project tree satisfying the archive contract."""
    directories = {"app", "config", "docs", "notebooks", "src", "tests", "tools", "scripts", "results"}
    for item in INCLUDE_PATHS:
        path = root / item
        if item in directories:
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"source for {item}\n", encoding="utf-8")
    for required in REQUIRED_ENTRIES:
        path = root / required
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(f"required {required}\n", encoding="utf-8")
    (root / "src" / "module.py").write_text("value = 1\n", encoding="utf-8")
    (root / "src" / "__pycache__").mkdir()
    (root / "src" / "__pycache__" / "discard.pyc").write_bytes(b"compiled")
    (root / "src" / "generated.zip").write_bytes(b"nested archive")
    (root / "docs" / ".DS_Store").write_bytes(b"mac metadata")
    (root / "results" / "run_0002").mkdir()
    (root / "results" / "run_0002" / "private.txt").write_text("excluded")


def test_review_zip_is_byte_identical_across_rebuilds_and_excludes_artifacts(
    tmp_path: Path,
) -> None:
    """Identical source bytes yield identical ZIP bytes independent of file mtimes."""
    project = tmp_path / "project"
    project.mkdir()
    _make_minimal_project(project)
    first = make_review_zip(tmp_path / "first.zip", project)

    source = project / "src" / "module.py"
    os.utime(source, (1_700_000_000, 1_700_000_000))
    second = make_review_zip(tmp_path / "second.zip", project)

    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        names = archive.namelist()
        assert names == sorted(names)
        assert set(REQUIRED_ENTRIES).issubset(names)
        assert not any("__pycache__" in name or name.endswith(".zip") for name in names)
        assert "docs/.DS_Store" not in names
        assert "results/run_0002/private.txt" not in names
        assert all(item.date_time == (1980, 1, 1, 0, 0, 0) for item in archive.infolist())
        assert all(item.create_system == 3 for item in archive.infolist())
