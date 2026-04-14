#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ -x "$ROOT_DIR/.venv/bin/uvicorn" ]]; then
  UVICORN_BIN="$ROOT_DIR/.venv/bin/uvicorn"
elif [[ -x "$ROOT_DIR/venv/bin/uvicorn" ]]; then
  UVICORN_BIN="$ROOT_DIR/venv/bin/uvicorn"
else
  echo "uvicorn not found in .venv/bin or venv/bin" >&2
  exit 1
fi

exec "$UVICORN_BIN" app.main:app --host 0.0.0.0 --port 8000
