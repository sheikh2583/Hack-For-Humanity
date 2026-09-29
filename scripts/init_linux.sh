#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

SKIP_ASSET_SETUP=0
ASSET_ARGS=()
for argument in "$@"; do
  if [[ "$argument" == "--skip-assets" ]]; then
    SKIP_ASSET_SETUP=1
  else
    ASSET_ARGS+=("$argument")
  fi
done

if [[ -x .venv/bin/python ]]; then
  PYTHON=".venv/bin/python"
else
  PYTHON=""
  for candidate in python3.11 python3.12; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON="$candidate"
      break
    fi
  done
  if [[ -z "$PYTHON" ]]; then
    echo "Python 3.11 or 3.12 is required. Install one, then rerun this script." >&2
    exit 2
  fi
  "$PYTHON" -m venv .venv
  PYTHON=".venv/bin/python"
fi

"$PYTHON" -c 'import sys; assert sys.version_info[:2] in {(3, 11), (3, 12)}, f"Unsupported Python: {sys.version}"'
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -e '.[dev,detect,training]' -r requirements-gpu-cu130.txt
if [[ "$SKIP_ASSET_SETUP" -eq 0 ]]; then
  "$PYTHON" scripts/prepare_training_assets.py "${ASSET_ARGS[@]}"
fi

cat <<'EOF'

Environment setup is complete. No GPU training or smoke test was started.
From the project root, run the smoke test explicitly:
  bash scripts/train_linux.sh smoke
After it passes, start or resume the configured full stages:
  bash scripts/train_linux.sh full
For help/options, use: .venv/bin/python scripts/train.py --help
EOF
