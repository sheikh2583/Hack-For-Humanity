"""M9 deploy-file sanity checks (no network, no Streamlit)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _requirements() -> list[str]:
    lines = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    return [line.split("#")[0].strip() for line in lines if line.split("#")[0].strip()]


def test_ui_stack_is_pinned_and_gpu_stack_is_absent() -> None:
    reqs = _requirements()
    assert "streamlit-folium==0.27.4" in reqs
    assert any(r.startswith("streamlit>=1.66") and "<1.67" in r for r in reqs)
    assert any(r.startswith("folium>=0.20") and "<0.21" in r for r in reqs)
    assert not any(re.match(r"(torch|torchvision|ultralytics|rasterio)", r) for r in reqs)
    assert not any(r.startswith("-") for r in reqs)


def test_keep_warm_workflow_uses_a_secret_and_a_schedule() -> None:
    yaml = pytest.importorskip("yaml")
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "keep_warm.yml").read_text(encoding="utf-8"))
    triggers = workflow.get("on") or workflow.get(True)
    assert "schedule" in triggers and "workflow_dispatch" in triggers
    text = (ROOT / ".github" / "workflows" / "keep_warm.yml").read_text(encoding="utf-8")
    assert "secrets.DHOA_APP_URL" in text


def test_demo_script_fits_three_minutes() -> None:
    text = (ROOT / "docs" / "DEMO_SCRIPT.md").read_text(encoding="utf-8")
    stamps = re.findall(r"\| (\d):(\d\d)-(\d):(\d\d) \|", text)
    assert stamps
    previous_end = 0
    for m1, s1, m2, s2 in stamps:
        start, end = int(m1) * 60 + int(s1), int(m2) * 60 + int(s2)
        assert start == previous_end and end > start
        previous_end = end
    assert previous_end == 180


def test_no_secrets_or_keys_in_deploy_files() -> None:
    for path in (ROOT / "docs" / "DEPLOY.md", ROOT / ".github" / "workflows" / "keep_warm.yml", ROOT / "tools" / "keep_warm.py"):
        assert not re.search(r"(api[_-]?key|token)\s*[:=]\s*['\"]?[A-Za-z0-9]{16,}", path.read_text(encoding="utf-8"), re.I)


def test_tools_are_importable_syntax() -> None:
    import ast

    for name in ("keep_warm", "measure_memory", "freeze_deploy_requirements", "benchmark_dashboard"):
        ast.parse((ROOT / "tools" / f"{name}.py").read_text(encoding="utf-8"))
