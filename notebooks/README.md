# Training Notebooks

Training notebook for Windows and Linux local NVIDIA GPUs, Colab, or Kaggle.
Use the OS-specific initialization script from the repository root to install
the shared pinned GPU stack and Jupyter runtime before opening the notebook.

## train.ipynb

Optional Jupyter interface for the shared YOLOv8 OBB runner, classes FCBK and
Zigzag. `scripts/train.py` and `config/training.yaml` are the source of truth
for Linux and Windows. Run the smoke cell first, then manually execute the full
cell. It trains yolov8n-obb at imgsz 256/384/512, then yolov8s-obb at the best
size; selects by validation mAP50 and evaluates the held-out test split once.
Numbered run state, GPU metadata, metric CSV chunks, and checkpoints are
organized under `results/run_NNNN/`. The runner stages the manifest and metric
chunks but leaves commits to the user; checkpoint artifacts remain ignored.

Use a dataset converted after the 1300 m Chebyshev leakage-filter change; the
notebook warns if `split_report.json` predates it.
