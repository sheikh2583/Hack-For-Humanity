# Claude Web review prompt

Upload `kilnwatch_bd_share.zip` to Claude Web, then paste this prompt:

```text
Review the attached KilnWatch BD project as an independent technical reviewer. Read `AGENTS.md`, `docs/PROGRESS.md`, `docs/TRAINING_READINESS.md`, `docs/MEMORY_AND_DOWNLOADS.md`, and `kilnwatch_scaffold.md` first. Inspect the actual code/config/notebook in the ZIP before making claims. Use web search for source-dependent claims and cite primary sources with direct links. Do not edit code or invent data formats, legal rules, thresholds, dates, or coordinates.

## Current verified project state

- The local converted dataset is at `data/interim/yolo_obb/`: train 8,058 images/labels, val 1,662, test 1,530; about 350.7 MiB total. `dataset.yaml` names FCBK and Zigzag. The split report records a 1,300 m Chebyshev filter and 1,322.41 m minimum cross-split distance.
- Latest full test run: 82 passed; Ruff clean. The environment used Python 3.12.10, although the project targets Python 3.11.
- Local PyTorch is CPU-only (`2.14.0+cpu`; CUDA unavailable). No training run or pretrained checkpoint exists. The notebook now requires CUDA, a reachable dataset path, and Ultralytics >=8.1; it runs the 3-epoch `yolov8n-obb` smoke test before full training.
- Before smoke training, the converted dataset must be uploaded/attached to Colab/Kaggle and `DATASET_ROOT` set to that location. A persistent Drive output path is needed if artifacts must survive runtime reset. Internet or cached `yolov8n-obb.pt` weights are needed at first use.
- Memory/download changes: raster tiles stream one window at a time; converter batch size is tunable; OSM caches are reused unless `kilnwatch fetch-osm --refresh` is used; Folium backgrounds no longer request remote tiles; the notebook skips the Ultralytics install if version >=8.1 is already present. No full-data RAM/VRAM benchmark was run.
- Training the existing converted chips is not blocked by the unresolved imagery-date conflict or `preprocessing_verified: false`. Those block Earth Engine parity/export claims, not the training job.

## Questions for review

1. SentinelKilnDB dates conflict. The authors' downloader currently says 2024-01-01 through 2025-02-28; the authors' README and NeurIPS supplement say September 2023 through February 2024; the Hugging Face card says November 2023 through February 2024. Determine whether primary sources resolve which dates produced the released chips. Give evidence/confidence and exact questions for the dataset authors if unresolved.
2. `config/preprocessing.yaml` intentionally remains `preprocessing_verified: false`; Earth Engine authentication/export and real paired-chip calibration have not run. Identify the evidence/checks required before enabling export, without guessing beyond the recorded recipe.
3. Rule values are unverified. Identify legal claims that appear unsupported by the attached dossier and point to the exact dossier passage needing review. Do not propose replacement thresholds or legal conclusions.
4. Review `docs/MEMORY_AND_DOWNLOADS.md` and the implemented changes. Identify any remaining unnecessary downloads or high-memory code paths visible in the source. Separate code-inspection findings from measured results; none of the optimizations has a full-data memory benchmark yet.
5. Compare the scaffold with actual implementation and identify missing items relevant to a credible pilot/handoff. The progress notes say `docs/legal_basis.md` and `docs/RUNBOOK.md`, railways and optional HDX/WDPA forest loaders, the 15 negative-region audit samples, the Chapainawabganj 2022 count check, and the Gazipur closed-kiln check/CSV remain incomplete. Verify those claims against the ZIP and correct any stale status.
6. Assess what the 82-test/Ruff result establishes and does not establish across Python 3.11 vs the checked Python 3.12 environment. Do not claim GPU training, live OSM, Earth Engine, or real-raster inference was validated.

## Return

- Is the project ready for the training smoke test, local demo, real imagery pilot, or none? Distinguish each clearly.
- A prioritized blocker table with evidence, next action, owner (developer/human/dataset author), and dependencies.
- Exact author clarification questions for the date conflict.
- Specific discrepancies between the ZIP contents and progress docs, with file paths.
- The shortest practical next-step sequence to start the hosted smoke test and then advance toward a pilot.

Be explicit about uncertainty. Separate verified facts, code-inspection conclusions, and inference. Do not recommend marking preprocessing or legal rules verified without evidence.
```
