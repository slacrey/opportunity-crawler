#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Starts only the opportunity_crawler Vue frontend for local development.
CONTROL_PLANE_HOST="${OPPORTUNITY_CRAWLER_CONTROL_PLANE_HOST:-127.0.0.1}"
CONTROL_PLANE_PORT="${OPPORTUNITY_CRAWLER_CONTROL_PLANE_PORT:-8000}"
FRONTEND_HOST="${OPPORTUNITY_CRAWLER_FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${OPPORTUNITY_CRAWLER_FRONTEND_PORT:-5173}"
API_BASE_URL="http://${CONTROL_PLANE_HOST}:${CONTROL_PLANE_PORT}"
VITE_API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-$API_BASE_URL}"

cd "$ROOT_DIR"

if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  echo "Missing frontend dependencies. Run: npm --prefix frontend install" >&2
  exit 1
fi

echo "Starting frontend at http://${FRONTEND_HOST}:${FRONTEND_PORT}"
echo "Proxying /api and /api/agents/ws to ${VITE_API_PROXY_TARGET}"
VITE_API_PROXY_TARGET="$VITE_API_PROXY_TARGET" exec npm --prefix "$ROOT_DIR/frontend" run dev -- \
  --host "$FRONTEND_HOST" \
  --port "$FRONTEND_PORT" \
  "$@"
