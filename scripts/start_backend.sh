#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

# Starts only the opportunity_crawler backend control plane for local development.
CONTROL_PLANE_HOST="${OPPORTUNITY_CRAWLER_CONTROL_PLANE_HOST:-127.0.0.1}"
CONTROL_PLANE_PORT="${OPPORTUNITY_CRAWLER_CONTROL_PLANE_PORT:-8000}"

if [[ -n "${OPPORTUNITY_CRAWLER_PYTHON:-}" ]]; then
  PYTHON_CMD=("$OPPORTUNITY_CRAWLER_PYTHON")
elif command -v uv >/dev/null 2>&1; then
  PYTHON_CMD=(uv run python)
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_CMD=("$ROOT_DIR/.venv/bin/python")
else
  PYTHON_CMD=(python3)
fi

cd "$ROOT_DIR"
echo "Starting control plane at http://${CONTROL_PLANE_HOST}:${CONTROL_PLANE_PORT}"
echo "Development users: admin/admin-pass, biz/biz-pass"
exec "${PYTHON_CMD[@]}" "$ROOT_DIR/scripts/run_control_plane_dev.py" "$@"
