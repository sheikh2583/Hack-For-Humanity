#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
PYTHON=".venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "Missing .venv. Run: bash scripts/init_linux.sh" >&2
  exit 2
fi
if [[ $# -eq 0 || "$1" == -* ]]; then
  set -- start "$@"
fi
exec "$PYTHON" scripts/train.py "$@"
