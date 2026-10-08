# Historical Windows RTX 4070 training evidence

This directory preserves the non-weight records recovered from the ignored
`runs/` outputs in this checkout. The source files' Windows filesystem
modification dates are 2026-09-29; treat that date as local file metadata,
not as a signed training timestamp.

## Machine and environment recorded in the console output

- Windows host; NVIDIA GeForce RTX 4070 Laptop GPU, 8,188 MiB reported by
  PyTorch.
- Python 3.12.10, PyTorch 2.14.0+cu130, Ultralytics 8.4.165.
- YOLOv8n-OBB, image size 256, batch 8, workers 0, seed 0, patience 10.
- The smoke run completed 3 epochs. Its last CSV row records mAP50 0.52184
  and mAP50-95 0.25290.
- The full 50-epoch YOLOv8n-256 attempt has six completed validation rows.
  The retained console output ends during epoch 7; this was an interrupted
  run, not a completed model evaluation.

## Files

- `smoke/args.yaml` and `smoke/results.csv`: Ultralytics arguments and the
  three smoke metric rows.
- `full_yolov8n_obb_256/args.yaml` and `results.csv`: arguments and six
  completed metric rows for the interrupted stage.
- `full_yolov8n_obb_256/console.log`: captured console output, including
  machine/runtime details and the last partial epoch.

Weights and plots were not copied. This historical run has no original run
manifest, dataset fingerprint, source revision, or complete epoch-7 metric row;
those details cannot be reconstructed from the files retained here. Hashes
below identify the preserved files after recovery into this repository.

## SHA-256

| File | SHA-256 |
|---|---|
| `smoke/args.yaml` | `92d5f8346c80efd628985b43d1a6ac0d65c31912e4675281f2de73b5f89932ae` |
| `smoke/results.csv` | `0f7dbedbac337b49c11d5a409ab7199ff906f6340754670095c1c6cb07653c68` |
| `full_yolov8n_obb_256/args.yaml` | `d8a5ca5bb65acd5dab0299b5ecb2640e6c4ac010495196ca4649654f1ab62b1c` |
| `full_yolov8n_obb_256/results.csv` | `9f4a68819f4b35d5f81c0efeb76152d38a7e1db9b37562422af163b5b382085d` |
| `full_yolov8n_obb_256/console.log` | `6499c1fdf0658707dc4634c298643ddd988441a079aa3155034e14853d0ab5b2` |
