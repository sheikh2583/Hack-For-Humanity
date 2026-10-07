"""Synthetic tests for portable training configuration and run identity."""

import json
from pathlib import Path

import pytest

from src.training.run_store import (
    allocate_run,
    dataset_fingerprint,
    load_run,
    read_training_config,
    write_json,
)


def test_dataset_fingerprint_tracks_paths_and_metadata(tmp_path: Path) -> None:
    """Fingerprint includes dataset metadata and the split file inventory."""
    for split in ("train", "val", "test"):
        images = tmp_path / split / "images"
        images.mkdir(parents=True)
        (images / "one.png").write_bytes(b"image")
    (tmp_path / "dataset.yaml").write_text("names: [kiln]\n", encoding="utf-8")
    (tmp_path / "split_report.json").write_text('{"filter": 1300}\n', encoding="utf-8")
    initial = dataset_fingerprint(tmp_path)
    (tmp_path / "train/images/two.png").write_bytes(b"more")
    assert dataset_fingerprint(tmp_path) != initial


def test_reads_shared_stage_config(tmp_path: Path) -> None:
    """Validate required fields for each declared model stage."""
    path = tmp_path / "training.yaml"
    valid = (
        "stages:\n"
        "  - {name: n256, model: n.pt, imgsz: 256, epochs: 3}\n"
        "  - {name: n384, model: n.pt, imgsz: 384, epochs: 3}\n"
        "  - {name: n512, model: n.pt, imgsz: 512, epochs: 3}\n"
    )
    path.write_text(valid, encoding="utf-8")
    assert read_training_config(path)["stages"][0]["name"] == "n256"
    path.write_text(
        "stages:\n"
        "  - {name: n256, model: n.pt, imgsz: 256, epochs: 3}\n"
        "  - {name: n384, model: n.pt, imgsz: 384, epochs: 3}\n"
        "  - {name: incomplete}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="name/model/imgsz/epochs"):
        read_training_config(path)


def test_run_state_is_atomic_json_and_validated(tmp_path: Path) -> None:
    """Write and reload state for a sequentially allocated run number."""
    run_id, run_dir = allocate_run(tmp_path)
    state = {"run_id": run_id, "status": "smoke"}
    write_json(run_dir / "run.json", state)
    assert json.loads((run_dir / "run.json").read_text(encoding="utf-8")) == state
    assert load_run(tmp_path, run_id) == state
    with pytest.raises(ValueError, match="Invalid run number"):
        load_run(tmp_path, "../escape")


# ---------------------------------------------------------------------------
# Selection metric, output location, and smoke gate (CPU-only, fake Ultralytics)
# ---------------------------------------------------------------------------

_HEADER = "epoch,time,metrics/precision(B),metrics/recall(B),metrics/mAP50(B),metrics/mAP50-95(B)\n"


def _write_results(path: Path, rows: list[tuple[float, float]], header: str = _HEADER) -> Path:
    """Write a results.csv whose rows are (mAP50, mAP50-95)."""
    body = "".join(f"{i + 1},{i},0.5,0.5,{m50},{m5095}\n" for i, (m50, m5095) in enumerate(rows))
    path.mkdir(parents=True, exist_ok=True)
    (path / "results.csv").write_text(header + body, encoding="utf-8")
    return path


def test_validation_map50_describes_best_checkpoint_not_last_row(tmp_path: Path) -> None:
    """best.pt is the max-mAP50-95 epoch; the last row (higher mAP50) must not be used."""
    from src.training.engine import validation_map50

    stage = _write_results(tmp_path / "s", [(0.40, 0.20), (0.50, 0.30), (0.60, 0.25), (0.62, 0.24)])
    assert validation_map50(stage, "metrics/mAP50(B)") == 0.50


def test_validation_map50_ties_nan_and_padded_header(tmp_path: Path) -> None:
    """First epoch wins ties, NaN fitness rows are skipped, and padded column names work."""
    from src.training.engine import validation_map50

    tie = _write_results(tmp_path / "tie", [(0.41, 0.30), (0.55, 0.30), (0.50, 0.10)])
    assert validation_map50(tie, "metrics/mAP50(B)") == 0.41
    nan = _write_results(tmp_path / "nan", [(0.9, float("nan")), (0.45, 0.2)])
    assert validation_map50(nan, "metrics/mAP50(B)") == 0.45
    padded = _write_results(
        tmp_path / "pad", [(0.3, 0.1), (0.4, 0.2)], header=_HEADER.replace(",", ",   ")
    )
    assert validation_map50(padded, "metrics/mAP50(B)") == 0.4


def test_validation_map50_rejects_missing_fitness_column(tmp_path: Path) -> None:
    """Without mAP50-95 the best epoch cannot be identified, so fail loudly."""
    from src.training.engine import validation_map50

    stage = _write_results(
        tmp_path / "s", [(0.4, 0.2)], header="epoch,time,a,b,metrics/mAP50(B),other\n"
    )
    with pytest.raises(ValueError, match="mAP50-95"):
        validation_map50(stage, "metrics/mAP50(B)")


def test_validation_map50_does_not_substitute_map50_95(tmp_path: Path) -> None:
    """A missing mAP50 column must not silently return the mAP50-95 value."""
    stage = _write_results(
        tmp_path / "s", [(0.4, 0.2)],
        header="epoch,time,metrics/mAP50-95(B)\n",
    )
    with pytest.raises(ValueError, match=r"metrics/mAP50\(B\)"):
        validation_map50(stage, "metrics/mAP50(B)")


def _fake_ultralytics(monkeypatch: pytest.MonkeyPatch, *, save_dir_for) -> list[dict]:
    """Install a fake ``ultralytics.YOLO``; ``save_dir_for(kwargs)`` mimics get_save_dir."""
    import sys
    import types
    from types import SimpleNamespace

    calls: list[dict] = []

    class FakeYOLO:
        def __init__(self, weights: str) -> None:
            self.weights = weights

        def add_callback(self, *_args: object) -> None:
            return None

        def train(self, **kwargs: object) -> None:
            calls.append(kwargs)
            self.trainer = SimpleNamespace(save_dir=save_dir_for(kwargs))

    module = types.ModuleType("ultralytics")
    module.YOLO = FakeYOLO  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ultralytics", module)
    return calls


_CONFIG = {
    "batch": 8, "workers": 0, "patience": 10, "seed": 0, "archive_interval": 10,
    "augmentation": {"flipud": 0.5, "degrees": 90},
}


def test_train_stage_passes_absolute_project_and_checks_location(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A relative project would land in Ultralytics' runs/<task>/; it must be absolute."""
    from src.training.engine import train_stage

    calls = _fake_ultralytics(
        monkeypatch, save_dir_for=lambda kw: Path(str(kw["project"])) / str(kw["name"])
    )
    checkpoints = tmp_path / "results" / "run_0001" / "checkpoints"
    out = train_stage(
        weights=tmp_path / "w.pt", data_yaml=tmp_path / "d.yaml", checkpoints_dir=checkpoints,
        logs_dir=tmp_path / "logs", stage_name="n256", imgsz=256, epochs=3,
        config=_CONFIG, device="cpu",
    )
    (kwargs,) = calls
    assert Path(str(kwargs["project"])).is_absolute()
    assert Path(str(kwargs["project"])) == checkpoints.resolve()
    assert kwargs["name"] == "n256" and kwargs["exist_ok"] is True
    assert kwargs["flipud"] == 0.5 and kwargs["degrees"] == 90 and kwargs["seed"] == 0
    assert out == checkpoints / "n256"


def test_train_stage_raises_when_ultralytics_wrote_elsewhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E.g. a checkpoint resumed from another host restores that host's save_dir."""
    from src.training.engine import train_stage

    _fake_ultralytics(monkeypatch, save_dir_for=lambda kw: tmp_path / "elsewhere" / "n256")
    with pytest.raises(RuntimeError, match="expected"):
        train_stage(
            weights=tmp_path / "w.pt", data_yaml=tmp_path / "d.yaml",
            checkpoints_dir=tmp_path / "ck", logs_dir=tmp_path / "logs", stage_name="n256",
            imgsz=256, epochs=3, config=_CONFIG, device="cpu", resume=True,
        )


def test_smoke_gate_fails_when_no_epochs_were_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A smoke run with a missing/short results.csv must not be marked as passed."""
    from src.training import runner

    models = tmp_path / "models"
    models.mkdir()
    (models / "n.pt").write_bytes(b"weights")
    config = {**_CONFIG, "models_dir": str(models), "smoke": {"model": "n.pt", "imgsz": 256, "epochs": 3}}
    saved: list[dict] = []
    monkeypatch.setattr(runner, "_record_hardware", lambda *a, **k: {"event_number": 1})
    monkeypatch.setattr(runner, "_save_state", lambda _run_dir, state: saved.append(dict(state)))
    monkeypatch.setattr(runner, "train_stage", lambda **kw: kw["checkpoints_dir"] / kw["stage_name"])

    state: dict = {"smoke": {"status": "pending"}}
    with pytest.raises(RuntimeError, match="expected 3"):
        runner._run_smoke("run_0001", tmp_path / "run", state, config, tmp_path / "d.yaml", "cpu")
    assert state["smoke"]["status"] == "failed" and state["status"] == "smoke_failed"

    # Same call with a complete 3-row CSV passes.
    ok_dir = _write_results(tmp_path / "run" / "checkpoints" / "smoke", [(0.1, 0.1)] * 3)
    monkeypatch.setattr(runner, "train_stage", lambda **kw: ok_dir)
    state = {"smoke": {"status": "pending"}}
    runner._run_smoke("run_0001", tmp_path / "run", state, config, tmp_path / "d.yaml", "cpu")
    assert state["smoke"]["status"] == "passed" and state["smoke"]["completed_epochs"] == 3
