# Numbered training results

Each run creates `run_NNNN/` with:

- `run.json`: dataset fingerprint, run status, host/GPU identity by stage,
  training config snapshot/hash, source revision and working-tree state, and
  portable checkpoint references. The runner stages this manifest in Git.
- `checkpoints/`: Ultralytics run folders, final model, and plots. This folder
  is ignored by Git because it contains model weights and generated artifacts.
- `logs/<stage>/`: CSV metric archives for each ten-epoch interval and any
  final partial interval. The runner stages new CSV chunks in Git.

Run folders are sequential and never overwritten. The manifest and metric
archives are Git-trackable; commits remain manual. To continue a run on another
machine, copy its complete `results/run_NNNN/` folder and the same dataset, then
run `scripts/train.py continue --run-id run_NNNN`.

Historical Windows RTX 4070 non-weight evidence recovered from ignored
`runs/` is collected under `legacy_windows_rtx4070_20260929/`. Its README
describes missing provenance that cannot be reconstructed. Do not copy model
weights into the Git-tracked evidence directory.
