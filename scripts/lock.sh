#!/usr/bin/env bash
# Generate a FULL transitive lock; requires a connected Python/PyPI resolver.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: Install uv first (https://docs.astral.sh/uv/)." >&2
  exit 2
fi
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON_BIN is missing. Install Python 3.11 before generating a lockfile." >&2
  exit 2
fi
# Resolve for the reference Python minor version; test wheel availability in CI.
uv pip compile --python-version 3.11 --generate-hashes \
  requirements.txt requirements-dev.txt -o requirements.lock
# Ensure no dependency escapes the lock as an unpinned range.
"$PYTHON_BIN" - <<'PY'
from pathlib import Path
lines = Path('requirements.lock').read_text(encoding='utf-8').splitlines()
items = [
    s.strip()
    for s in lines
    if s.strip() and not s.lstrip().startswith('#') and not s.startswith(' ')
]
invalid = [s for s in items if s and s[0].isalnum() and '==' not in s]
if invalid:
    raise SystemExit(f'Unpinned entries: {invalid}')
print(f"Full lock generated: {len([x for x in items if '==' in x])} packages")
PY
