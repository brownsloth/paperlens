#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d frontend/dist ]] || [[ "${REBUILD_FRONTEND:-}" == "1" ]]; then
  echo "Building public frontend…"
  (cd frontend && npm run build:public)
fi

source .venv/bin/activate 2>/dev/null || true
export PORT="${PORT:-8080}"
echo "Starting public PaperLens on port $PORT (use npm run dev:public in frontend/)"
exec uvicorn backend.app.public_main:app --host 0.0.0.0 --port "$PORT"
