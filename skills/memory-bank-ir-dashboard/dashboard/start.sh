#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
if ! python -c 'import flask, cryptography' >/dev/null 2>&1; then
    pip install -q -r requirements.txt
fi

exec python app.py "$@"
