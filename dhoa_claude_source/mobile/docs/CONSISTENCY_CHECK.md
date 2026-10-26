# Consistency Check

**Date:** 2026-10-11

## Results

- The dashboard renders its amber advisory on every run, before selecting or loading the data file. The message is not conditional on any `verified` flag.
- `config/preprocessing.yaml` remains `preprocessing_verified: false`. The exporter logs this state and stops before Earth Engine initialization; the dashboard does not display this configuration warning.
- Model metrics are reported in `docs/ARCHITECTURE.md` and `docs/ROUND2_SUBMISSION.md` as mAP50 0.752, mAP50-95 0.493, Precision 0.699, Recall 0.734, FCBK AP50 0.601, and Zigzag AP50 0.904. Both documents identify these as held-out SentinelKilnDB chip test results, not raster-pilot performance.
- The five districts are configured and listed consistently: Chapainawabganj, Gazipur, Rajshahi, Dhaka, and Chittagong.
- The architecture, submission, and README cite SentinelKilnDB, Mondal et al., NeurIPS 2025, CC BY-NC 4.0.
- The runbook names `results/run_0002/checkpoints/final/best.pt` and inference size 512.
- Tests: **189 passed**. Ruff: **All checks passed**. Pytest emitted 10 warnings (6 Rasterio pending deprecations and 4 expected rule-configuration warnings).

## Files changed in this audit

- `README.md` — rewrote the project overview for the Round 2 prototype, five pilot districts, current checkpoint and quick-start commands; added advisory wording and dataset attribution/licence; removed unsupported candidate-count claim.
- `app/streamlit_app.py` — render the amber advisory unconditionally near the top of the dashboard.
- `app/popup.py` — use advisory popup language and sanitize presentation strings.
- `app/presentation.py` — use screening language in CSV output.
- `config/rules.yaml` — corrected explanatory comments only; no threshold, coordinate, or `verified` value changed.
- `src/data/export_s2.py` — emit a log warning and fail closed when preprocessing is not verified, before Earth Engine initialization.
- `src/data/convert_sentinelkilndb.py` — clarify source taxonomy and output-class mapping.
- `scripts/make_review_zip.py` — changed CLI status wording from “verified” to “checked”.
- `scripts/prepare_training_assets.py` — changed a status message from “verified” to “checked”.
- `docs/ARCHITECTURE.md` — add the requested model metrics, source scope, citation and advisory limitations; describe audit observations with appropriate sampling limits.
- `docs/ROUND2_SUBMISSION.md` — add the requested model metrics and citation; align districts, current candidate-row counts, audit wording and limitations with repository evidence.
- `docs/DEMO_SCRIPT.md` — align five-district walkthrough and language with the current advisory dashboard.
- `docs/RUNBOOK.md` — clarify that its state is recorded history and retain the current checkpoint and 512-pixel command.
- `docs/PROGRESS.md`, `docs/TRAINING_READINESS.md`, `docs/CLAUDE_REVIEW_CONTEXT.md`, `docs/CLAUDE_WEB_PROMPT.md`, `CLAUDE_CONTEXT_2026-10-08.md`, and `kilnwatch_scaffold.md` — clarify historical notes and remove/correct stale current-state descriptions.
- `docs/assumptions.md` — document the observed underscore filename convention and class mapping.
- `data/raw/sentinelkilndb/README.md` — correct source image-name examples and clarify source labels versus model output classes.
- `temporary doc share/KilnWatch_BD_Next_Steps.md` — use advisory language in the demo guidance.
- `tests/test_dashboard_presentation.py`, `tests/test_dashboard_filters.py`, `tests/test_popup.py`, `tests/test_priority.py`, `tests/test_rules.py`, and `tests/test_export_s2.py` — align presentation assertions and add synthetic coverage for unconditional advisory rendering and preprocessing refusal/logging.

No changes were made to `config/aoi.yaml`, `config/preprocessing.yaml`, model weights, or numeric rule thresholds. `config/rules.yaml` still has three siting rules and one technology entry, all with `verified: false`.

## Human decisions required

1. **Rule count and rule status:** The request refers to six siting rules, while the active configuration contains three siting rules (`near_school`, `near_hospital`, `near_settlement`) plus a technology heuristic. Which six rules are intended, and should `verified: true` mean only that an Act threshold was located, or also that the configured map feature and geometry correctly represent the statutory category? I left all flags unchanged because generic mapped features do not establish the legally controlling boundaries or categories. The official consolidated Act is [Act 59 of 2013, section 8](https://bdlaws.minlaw.gov.bd/act-print-1140/section-print-43613.html); the project’s own legal evidence register records unresolved interpretation and mapping questions.
2. **2022 clearance count:** Can you provide or identify the Department of Environment register supporting the “112 kilns without valid clearance” statement? The submission now attributes it to the project brief and says the underlying source was not independently checked in this repository.
3. **Audit evidence:** Are the older 30-candidate Google Earth review records and the later 20-row review available for source verification? The repository text describes the 17/30 and 15/15 observations as exploratory and keeps the review rounds separate; I did not independently inspect external imagery or validate the labels.
4. **Dashboard demonstration:** Please check the rendered dashboard with the intended final data file and checkpoint, including popup fields, filters, CSV download, and load timestamp. The app was not launched against full pilot data in this audit.
5. **Dataset licence and citation:** Please confirm the project’s rights to redistribute/use the downloaded SentinelKilnDB copy and verify the citation/CC BY-NC 4.0 terms against the dataset’s authoritative release before publication. This audit checked repository documentation, not a licence review.

## Stale or contradictory content retained

- YOLOv8n, 256-pixel, and smoke-run references remain in the training configuration/history, model training tests, and archived `results/legacy_windows_rtx4070_20260929` artifacts. These describe historical experiments or test fixtures; they are not represented as the current selected checkpoint. They were retained as experiment provenance.
- `CFCBK` remains in source-dataset metadata and the source-to-output converter because it is an original SentinelKilnDB label mapped to the project’s FCBK output. It is not presented as a third detector output class.
- Internal compatibility fields such as `breached_rules`, `breach_score`, and `rules_verified` remain in Python and persisted pipeline schemas. Renaming them would change data/API contracts; dashboard and CSV presentation use user-facing wording. Sanitizer and test cases also contain prohibited terms as inputs to ensure they are rewritten.
- Historical legal research documents retain status terms such as “verified” or “confirmed” when describing evidence-review state. The `verified` configuration field and Python identifiers are also retained per the request’s exception. The active rule flags remain false pending the decision above.
- The project’s current processed output records 2,150 candidate rows, not 4,000+. The submission uses the current local count and lists per-district counts; the larger estimate was not adopted.
- `docs/RUNBOOK.md` still contains historical notes that a prior raster inference used a model trained at 256 pixels. It identifies the current checkpoint and 512-pixel run command separately; the historical note was retained for provenance.

## Checks and limits

- `python -m pytest -q`: **189 passed**, 10 warnings.
- `python -m ruff check .`: **All checks passed**.
- `git diff --check`: reported one trailing-space line in the README heading; that whitespace was removed after the check. Rerun `git diff --check` to confirm the final working tree.
- No GPU, Earth Engine export, training, or inference was run. The legal meaning of project flags, external audit labels, source-register claims, licence terms, and live dashboard appearance remain unverified by this repository-only check.
