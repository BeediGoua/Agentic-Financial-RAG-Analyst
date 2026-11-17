#!/usr/bin/env bash
# ONE command: repository-local tests, with no BRVM data/network required.
# Optional --full: also require OCR, Ollama and model weights to be available.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "ERROR: .venv is missing. Run: bash scripts/bootstrap.sh" >&2
  exit 2
fi
"$PY" scripts/check_env.py --profile core --strict
"$PY" -m compileall -q app scripts tests
"$PY" -m pytest -q tests
"$PY" -m pip check
if [[ "${1:-}" == "--full" ]]; then
  "$PY" scripts/check_env.py --profile full --strict
fi
