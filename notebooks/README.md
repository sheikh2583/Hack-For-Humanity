# Training Notebooks

Training notebooks for Colab/Kaggle GPU sessions.

## train.ipynb

YOLOv8 OBB training notebook (Step 3), classes FCBK and Zigzag:
- Writes an absolute-path copy of `dataset.yaml` at runtime and uses it for train/val/test
- Installs Ultralytics only when absent or below version 8.1
- Stops at setup if CUDA is unavailable; select a hosted GPU runtime first
- A 3-epoch smoke test (yolov8n-obb, imgsz 256) must pass before the full runs start
- Trains yolov8n-obb at imgsz 256/384/512, then yolov8s-obb at the best imgsz
  (50 epochs, patience 10, `flipud=0.5`, `degrees=90`, `seed=0`)
- Picks the best run by **val** mAP50, then evaluates that model on the **test**
  split exactly once
- Logs mAP50, mAP50-95 and per-class precision/recall/mAP50 (epochs run come from `results.csv`)
- Saves `best.pt`, `training_results.json`, and val/test confusion matrices and PR curves
  to `OUTPUT_DIR`

Use a dataset converted after the 1300 m Chebyshev leakage-filter change; the
notebook warns if `split_report.json` predates it.
