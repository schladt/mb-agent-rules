#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNTIME="$PROJECT_ROOT/.memory-bank/runtime/dashboard"
export PYTHONDONTWRITEBYTECODE=1
if [ ! -f "$PROJECT_ROOT/.memory-bank/dashboard.config.json" ]; then
    echo "Run dashboard setup after bank initialization/migration first" >&2
    exit 1
fi
UMASK="$(python3 -B - "$PROJECT_ROOT/.memory-bank/dashboard.config.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    config = json.load(handle)
print("007" if config.get("shared_group_access") is True else "077")
PY
)"
umask "$UMASK"
if [ -L "$PROJECT_ROOT/.memory-bank" ] || [ -L "$PROJECT_ROOT/.memory-bank/runtime" ] || [ -L "$RUNTIME" ]; then
    echo "Refusing symlinked dashboard runtime" >&2
    exit 1
fi
if [ -L "$RUNTIME/venv" ] || [ -L "$RUNTIME/cache" ]; then
    echo "Refusing symlinked environment/cache" >&2
    exit 1
fi
mkdir -p "$RUNTIME"
export XDG_CACHE_HOME="$RUNTIME/cache"
export PIP_CACHE_DIR="$RUNTIME/cache/pip"
if [ ! -d "$RUNTIME/venv" ]; then
    echo "Creating private virtual environment..."
    python3 -m venv "$RUNTIME/venv"
fi
source "$RUNTIME/venv/bin/activate"
if ! python -B -c 'import flask, cryptography' >/dev/null 2>&1; then
    python -B -m pip install -q -r "$SCRIPT_DIR/requirements.txt"
fi
exec python -B "$SCRIPT_DIR/app.py" "$@"
