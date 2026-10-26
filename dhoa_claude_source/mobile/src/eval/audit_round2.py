"""Analyze blinded Round 2 kiln-candidate labels.

Input schema: two label sheets with candidate IDs and human responses, a
separate sampling key, and band populations. Output schema: Markdown and CSV
summaries of screening precision, weighted estimates, class summaries, and
labeler agreement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

LABELS = {"TP", "FP", "SKIP"}
BANDS = ("low", "mid", "high")
THRESHOLDS = (0.30, 0.35, 0.40, 0.45, 0.50)


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Return a Wilson interval for a proportion, including empty/all-hit cases."""
    if total <= 0:
        return 0.0, 0.0
    proportion = successes / total
    denominator = 1 + z**2 / total
    center = (proportion + z**2 / (2 * total)) / denominator
    spread = z * np.sqrt(
        proportion * (1 - proportion) / total + z**2 / (4 * total**2)
    ) / denominator
    return max(0.0, center - spread), min(1.0, center + spread)


def normalize_labels(values: pd.Series, source: str) -> pd.Series:
    """Validate human response values and reject blanks with row context."""
    labels = values.astype("string").str.strip().str.upper()
    missing = labels.isna() | labels.eq("")
    if missing.any():
        rows = [int(index) + 2 for index in labels.index[missing][:10]]
        raise ValueError(f"Blank label in {source} at CSV row(s): {rows}")
    invalid = sorted(set(labels.dropna().unique()) - LABELS)
    if invalid:
        raise ValueError(f"Invalid label(s) in {source}: {invalid}; use TP, FP, or SKIP")
    return labels


def precision_summary(labels: pd.Series) -> dict[str, float | int | None]:
    """Summarize TP/(TP+FP), excluding SKIP responses."""
    normalized = labels.astype("string").str.upper()
    valid = normalized[normalized.isin(["TP", "FP"])]
    total = len(valid)
    successes = int(valid.eq("TP").sum())
    lower, upper = wilson_interval(successes, total)
    return {
        "n": total,
        "tp": successes,
        "fp": int(valid.eq("FP").sum()),
        "skip": int(normalized.eq("SKIP").sum()),
        "precision": successes / total if total else None,
        "ci_95_lower": lower if total else None,
        "ci_95_upper": upper if total else None,
    }


def weighted_precision(
    labels_by_band: dict[str, pd.Series],
    populations: dict[str, int],
    *,
    seed: int = 42,
    bootstrap_reps: int = 5000,
) -> dict[str, float | int | None]:
    """Compute a population-weighted estimate with a stratified bootstrap CI."""
    total_population = sum(int(populations.get(band, 0)) for band in BANDS)
    if total_population <= 0:
        raise ValueError("Band populations must sum to a positive value")
    weights = {band: populations.get(band, 0) / total_population for band in BANDS}
    valid_by_band = {
        band: labels_by_band.get(band, pd.Series(dtype="string"))
        .astype("string").str.upper().loc[lambda values: values.isin(["TP", "FP"])].to_numpy()
        for band in BANDS
    }
    if any(populations.get(band, 0) > 0 and len(valid_by_band[band]) == 0 for band in BANDS):
        return {"precision": None, "ci_95_lower": None, "ci_95_upper": None,
                "population": total_population, "weights": weights}
    observed = sum(
        weights[band] * float(np.mean(values == "TP"))
        for band, values in valid_by_band.items() if len(values)
    )
    rng = np.random.default_rng(seed)
    estimates = np.zeros(bootstrap_reps, dtype=float)
    for index in range(bootstrap_reps):
        estimates[index] = sum(
            weights[band] * float(np.mean(rng.choice(values, len(values), replace=True) == "TP"))
            for band, values in valid_by_band.items() if len(values)
        )
    lower, upper = np.quantile(estimates, [0.025, 0.975])
    return {
        "precision": float(observed),
        "ci_95_lower": float(lower),
        "ci_95_upper": float(upper),
        "population": total_population,
        "weights": weights,
    }


def cohen_kappa(first: pd.Series, second: pd.Series) -> tuple[float | None, float | None]:
    """Return exact-label percent agreement and Cohen's kappa."""
    left = first.astype("string").str.upper().to_numpy()
    right = second.astype("string").str.upper().to_numpy()
    if len(left) == 0:
        return None, None
    agreement = float(np.mean(left == right))
    categories = sorted(set(left) | set(right))
    expected = sum(float(np.mean(left == label) * np.mean(right == label)) for label in categories)
    kappa = 1.0 if expected == 1.0 else (agreement - expected) / (1 - expected)
    return agreement, kappa


def _read_sheet(path: Path, sheet_name: str) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"kiln_id": "string", "district": "string"})
    required = {"kiln_id", "district", "label", "kiln_class"}
    if not required.issubset(frame.columns):
        raise ValueError(f"{sheet_name} is missing required columns: {sorted(required - set(frame.columns))}")
    frame["label"] = normalize_labels(frame["label"], str(path))
    frame["_sheet"] = sheet_name
    return frame


def _read_population_table(path: Path) -> dict[str, dict[str, int]]:
    """Read district and confidence-band population counts from the sample report."""
    populations: dict[str, dict[str, int]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 6 or cells[0] not in {"Chapainawabganj", "Gazipur"} or cells[1] not in BANDS:
            continue
        try:
            populations.setdefault(cells[0], {})[cells[1]] = int(cells[2])
        except ValueError:
            continue
    if not populations:
        raise ValueError(f"No band population rows found in {path}")
    return populations


def _percent(value: float | None) -> str:
    return "not available" if value is None else f"{value:.1%}"


def analyze_round2(
    sheet_a: Path,
    sheet_b: Path,
    key_path: Path,
    sampling_report: Path,
    *,
    old_labels: Path | None = None,
    report_path: Path | None = None,
    csv_path: Path | None = None,
    seed: int = 42,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Analyze completed human label sheets and write Markdown and CSV reports."""
    a = _read_sheet(sheet_a, "A")
    b = _read_sheet(sheet_b, "B")
    key = pd.read_csv(key_path, dtype={"kiln_id": "string", "district": "string"})
    required_key = {"kiln_id", "district", "model_confidence", "band", "predicted_class", "is_overlap"}
    if not required_key.issubset(key.columns):
        raise ValueError(f"Audit key is missing required columns: {sorted(required_key - set(key.columns))}")
    if key.duplicated(["kiln_id", "district"]).any():
        raise ValueError("Audit key contains duplicate kiln_id/district rows")
    all_responses = pd.concat([a, b], ignore_index=True)
    all_responses = all_responses.merge(key, on=["kiln_id", "district"], how="left", validate="many_to_one")
    if all_responses["band"].isna().any():
        raise ValueError("A label sheet row has no matching audit key entry")
    unique_responses = all_responses.sort_values("_sheet").drop_duplicates(
        ["kiln_id", "district"], keep="first"
    ).copy()
    populations = _read_population_table(sampling_report)
    summary_rows: list[dict[str, Any]] = []
    district_results: dict[str, Any] = {}

    for district in ("Chapainawabganj", "Gazipur"):
        district_frame = unique_responses[unique_responses["district"] == district]
        district_result: dict[str, Any] = {"by_band": {}, "weighted": None}
        for band in BANDS:
            subset = district_frame[district_frame["band"] == band]
            values = precision_summary(subset["label"])
            values.update({"district": district, "band": band, "population": populations.get(district, {}).get(band, 0)})
            summary_rows.append({"metric": "district_band", **values})
            district_result["by_band"][band] = values
        weighted = weighted_precision(
            {band: district_frame.loc[district_frame["band"] == band, "label"] for band in BANDS},
            populations.get(district, {}), seed=seed,
        )
        district_result["weighted"] = weighted
        summary_rows.append({"metric": "population_weighted", "district": district,
                             "band": "all", **weighted, "n": len(district_frame)})
        district_results[district] = district_result

        class_rows = district_frame[district_frame["label"] != "SKIP"]
        for kiln_class, class_subset in class_rows.groupby("kiln_class", dropna=False):
            class_name = "blank" if pd.isna(kiln_class) or str(kiln_class).strip() == "" else str(kiln_class)
            class_summary = precision_summary(class_subset["label"])
            if class_summary["n"] >= 10:
                summary_rows.append({"metric": "human_kiln_class", "district": district,
                                     "band": class_name, **class_summary})
            else:
                summary_rows.append({"metric": "human_kiln_class", "district": district,
                                     "band": class_name, "n": class_summary["n"],
                                     "tp": class_summary["tp"], "fp": class_summary["fp"],
                                     "skip": 0, "precision": None,
                                     "ci_95_lower": None, "ci_95_upper": None,
                                     "note": "sample too small"})

        for cutoff in THRESHOLDS:
            retained = district_frame[pd.to_numeric(district_frame["model_confidence"]).ge(cutoff)]
            cutoff_summary = precision_summary(retained["label"])
            summary_rows.append({"metric": "exploratory_cutoff", "district": district,
                                 "band": f">={cutoff:.2f}", "cutoff": cutoff,
                                 "retained_sample_candidates": len(retained), **cutoff_summary,
                                 "note": "exploratory; not validated"})

    overlap = all_responses[all_responses["is_overlap"].astype(str).str.casefold().isin(["true", "1"])]
    pivot = overlap.pivot_table(index=["kiln_id", "district"], columns="_sheet", values="label", aggfunc="first")
    if not {"A", "B"}.issubset(pivot.columns):
        raise ValueError("Overlap candidates need labels from both sheets A and B")
    agreement, kappa = cohen_kappa(pivot["A"], pivot["B"])
    disagreements = [
        {"kiln_id": str(index[0]), "district": str(index[1]), "A": str(row.A), "B": str(row.B)}
        for index, row in pivot[pivot["A"] != pivot["B"]].iterrows()
    ]
    summary_rows.append({"metric": "overlap_agreement", "district": "all", "band": "all",
                         "n": len(pivot), "percent_agreement": agreement,
                         "cohen_kappa": kappa})

    old_result = None
    if old_labels is not None:
        old = pd.read_csv(old_labels)
        if "label" not in old.columns:
            raise ValueError(f"Old label file is missing label column: {old_labels}")
        old["label"] = normalize_labels(old["label"], str(old_labels))
        old_result = precision_summary(old["label"])
        summary_rows.append({"metric": "Chapainawabganj_old_30_separate", "district": "Chapainawabganj",
                             "band": "old_30", **old_result,
                             "note": "separate design; excluded from weighted estimate"})

    result_frame = pd.DataFrame(summary_rows)
    report_path = report_path or sheet_a.parent / "audit_round2_results.md"
    csv_path = csv_path or sheet_a.parent / "audit_round2_results.csv"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    result_frame.to_csv(csv_path, index=False)

    lines = [
        "# Round 2 screening audit results", "",
        "SKIP responses are excluded from precision calculations. The band-weighted estimate uses each band’s candidate population.",
        "Raw pooled precision is not a valid overall estimate because the confidence bands were sampled at different rates.",
        "", "## Precision by district and band", "",
        "| District | Band | Population | TP | FP | SKIP | Precision | 95% Wilson CI |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for district in district_results:
        for band in BANDS:
            row = district_results[district]["by_band"][band]
            ci = f"{_percent(row['ci_95_lower'])}–{_percent(row['ci_95_upper'])}"
            lines.append(f"| {district} | {band} | {row['population']} | {row['tp']} | {row['fp']} | {row['skip']} | {_percent(row['precision'])} | {ci} |")
    lines.extend(["", "## Population-weighted estimates", ""])
    for district, values in district_results.items():
        weighted = values["weighted"]
        lines.append(
            f"- {district}: {_percent(weighted['precision'])} "
            f"(stratified bootstrap 95% CI {_percent(weighted['ci_95_lower'])}–"
            f"{_percent(weighted['ci_95_upper'])}); eligible population {weighted['population']}."
        )
        if weighted["precision"] is None:
            lines.append("  Estimate unavailable because a populated band had no non-SKIP labels.")
    lines.extend(["", "## Human-entered class summary", "",
                  "False candidate responses use n/a and are not assigned to a kiln class.",
                  "", "| District | Human-entered class | TP | FP | SKIP | Precision | 95% Wilson CI |",
                  "|---|---|---:|---:|---:|---:|---:|"])
    for row in summary_rows:
        if row["metric"] != "human_kiln_class":
            continue
        if row.get("note") == "sample too small":
            precision_text, interval = "sample too small", "sample too small"
        else:
            precision_text = _percent(row.get("precision"))
            interval = f"{_percent(row.get('ci_95_lower'))}–{_percent(row.get('ci_95_upper'))}"
        lines.append(
            f"| {row['district']} | {row['band']} | {row['tp']} | {row['fp']} | "
            f"{row['skip']} | {precision_text} | {interval} |"
        )
    lines.extend(["", "## Two-labeler overlap", "",
                  f"- Overlap rows: {len(pivot)}; exact-label agreement: {_percent(agreement)}; Cohen’s kappa: {kappa if kappa is not None else 'not available'}.",
                  f"- Disagreements: {len(disagreements)}. SKIP versus TP/FP counts as disagreement."])
    if disagreements:
        lines.extend(["", "| kiln_id | District | A | B |", "|---|---|---|---|"])
        lines.extend(f"| {item['kiln_id']} | {item['district']} | {item['A']} | {item['B']} |" for item in disagreements)
    lines.extend(["", "## Exploratory confidence cutoffs", "",
                  "Exploratory; not validated. Judge cutoffs on Round 2 labels, not the earlier 30-label set.",
                  "Counts and intervals describe the sampled candidates retained above each cutoff.",
                  "", "| District | Confidence cutoff | Sample candidates retained | TP | FP | SKIP | Precision | 95% Wilson CI |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"])
    for row in summary_rows:
        if row["metric"] != "exploratory_cutoff":
            continue
        interval = f"{_percent(row.get('ci_95_lower'))}–{_percent(row.get('ci_95_upper'))}"
        lines.append(
            f"| {row['district']} | {row['band']} | {row['retained_sample_candidates']} | "
            f"{row['tp']} | {row['fp']} | {row['skip']} | {_percent(row.get('precision'))} | {interval} |"
        )
    if old_result is not None:
        lines.extend(["", "## Earlier Chapainawabganj 30-label set", "",
                      (f"Separate design; confidence was visible. Precision {_percent(old_result['precision'])} "
                       f"(95% Wilson CI {_percent(old_result['ci_95_lower'])}–{_percent(old_result['ci_95_upper'])}), "
                       f"n={old_result['n']}. Excluded from the weighted estimate.")])
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"districts": district_results, "agreement": agreement, "kappa": kappa,
            "disagreements": disagreements, "old_labels": old_result,
            "rows": result_frame}
