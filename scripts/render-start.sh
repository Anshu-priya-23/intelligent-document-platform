#!/usr/bin/env bash
set -euo pipefail
export TESSERACT_CMD="$PWD/.local/ocr/usr/bin/tesseract"
export LD_LIBRARY_PATH="$PWD/.local/ocr/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
export TESSDATA_PREFIX="$PWD/.local/ocr/usr/share/tesseract-ocr/5/tessdata"
if [[ "${DATABASE_URL:-}" != postgres* ]]; then
  echo "Set DATABASE_URL to an external PostgreSQL database for persistent deployment." >&2
  exit 1
fi
exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
