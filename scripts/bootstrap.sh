#!/usr/bin/env bash
# Deterministic entrypoint for a CLEAN Python virtual environment.
# Cannot work fully offline unless package wheels were cached beforehand.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

resolve_python_bin() {
  local candidate="${PYTHON_BIN:-}"
  if [[ -n "$candidate" ]] && command -v "$candidate" >/dev/null 2>&1; then
    echo "$candidate"
    return 0
  fi
  if command -v python3.11 >/dev/null 2>&1; then
    echo "python3.11"
    return 0
  fi
  if command -v uv >/dev/null 2>&1; then
    local uv_bin
    uv_bin="$(uv python find 3.11 2>/dev/null || true)"
    if [[ -n "$uv_bin" ]]; then
      echo "$uv_bin"
      return 0
    fi
  fi
  echo "ERROR: Python 3.11 is missing. Install it or set PYTHON_BIN to a valid interpreter." >&2
  return 2
}

PYTHON_BIN="$(resolve_python_bin)" || exit $?
"$PYTHON_BIN" - <<'PY'
import sys
if not ((3,11) <= sys.version_info[:2] < (3,14)):
    raise SystemExit('Python 3.11, 3.12 or 3.13 required.')
PY
if [[ ! -x .venv/bin/python ]]; then
  "$PYTHON_BIN" -m venv .venv
fi
PY="${ROOT}/.venv/bin/python"
"$PY" -m pip install --upgrade 'pip==25.1.1'
if [[ -f requirements.lock ]]; then
  echo "Using fully resolved requirements.lock"
  "$PY" -m pip install --requirement requirements.lock
else
  echo "WARNING: requirements.lock is absent. Direct pins only; transitive versions are NOT locked." >&2
  "$PY" -m pip install --requirement requirements.txt --requirement requirements-dev.txt
fi
"$PY" -m pip check
"$PY" scripts/check_env.py --profile core --strict
if [[ "${1:-}" != "--no-tests" ]]; then
  bash scripts/test.sh
fi
cat <<'MSG'
Environment installed. To check OCR, Ollama and model cache, run:
  .venv/bin/python scripts/check_env.py --profile full
To prepare/download models (network needed), run:
  .venv/bin/python scripts/prefetch_models.py --all
  ollama pull qwen2.5:7b
MSG
