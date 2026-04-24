#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

python3 -m opportunity_crawler.bootstrap.control_plane "$ROOT_DIR/packaging/defaults/control_plane.toml"
python3 -m opportunity_crawler.bootstrap.agent "$ROOT_DIR/packaging/defaults/agent.toml"
