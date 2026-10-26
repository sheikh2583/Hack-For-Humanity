"""M9 deploy-file sanity checks (no network, no Streamlit)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _requirements() -> list[str]:
    lines = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    return [line.split("#")[0].strip() for line in lines if line.split("#")[0].strip()]


def test_ui_stack_is_pinned_and_gpu_stack_is_absent() -> None:
    reqs = _requirements()
    assert "streamlit==1.66.1" in reqs
    assert "streamlit-folium==0.27.4" in reqs
    assert "folium==0.20.0" in reqs
    assert not any(r.lower().startswith(("torch", "torchvision", "ultralytics", "rasterio")) for r in reqs)
    assert not any(r.startswith("-") for r in reqs)


def test_cloud_entrypoint_selects_the_dashboard_requirements() -> None:
    local_requirements = (ROOT / "app" / "requirements.txt").read_text(encoding="utf-8").splitlines()
    entries = [line.split("#", 1)[0].strip() for line in local_requirements]
    assert [line for line in entries if line] == ["-r ../requirements.txt"]
    assert (ROOT / "uv.lock").is_file()
    assert (ROOT / "app" / "streamlit_app.py").is_file()


def test_cloud_python_version_and_runtime_data_are_present() -> None:
    assert (ROOT / "runtime.txt").read_text(encoding="utf-8").strip() == "python-3.12"
    assert (ROOT / "data" / "processed" / "kilns_prioritised.parquet").is_file()
    assert (ROOT / "config" / "rules.yaml").is_file()


def test_tools_are_importable_syntax() -> None:
    import ast

    for name in ("keep_warm", "measure_memory", "freeze_deploy_requirements", "benchmark_dashboard"):
        ast.parse((ROOT / "tools" / f"{name}.py").read_text(encoding="utf-8"))
