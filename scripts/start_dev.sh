#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

# Starts the opportunity_crawler control plane before the Vite frontend.
CONTROL_PLANE_HOST="${OPPORTUNITY_CRAWLER_CONTROL_PLANE_HOST:-127.0.0.1}"
CONTROL_PLANE_PORT="${OPPORTUNITY_CRAWLER_CONTROL_PLANE_PORT:-8000}"
API_BASE_URL="http://${CONTROL_PLANE_HOST}:${CONTROL_PLANE_PORT}"
BACKEND_PID=""

cleanup() {
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}

wait_for_backend() {
  for _ in {1..80}; do
    if [[ -n "$BACKEND_PID" ]] && ! kill -0 "$BACKEND_PID" 2>/dev/null; then
      echo "Control plane exited before becoming healthy." >&2
      wait "$BACKEND_PID"
    fi

    if python3 -c 'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=1).read()' "$API_BASE_URL/api/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done

  echo "Timed out waiting for $API_BASE_URL/api/health" >&2
  return 1
}

trap cleanup EXIT INT TERM
cd "$ROOT_DIR"

if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  echo "Missing frontend dependencies. Run: npm --prefix frontend install" >&2
  exit 1
fi

echo "Starting control plane at $API_BASE_URL"
python3 "$ROOT_DIR/scripts/run_control_plane_dev.py" &
BACKEND_PID=$!

wait_for_backend

echo "Starting frontend at http://127.0.0.1:5173"
echo "Development users: admin/admin-pass, biz/biz-pass"
VITE_API_PROXY_TARGET="$API_BASE_URL" npm --prefix "$ROOT_DIR/frontend" run dev
