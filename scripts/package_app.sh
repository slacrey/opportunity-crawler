#!/usr/bin/env bash
set -euo pipefail

# Packages the opportunity_crawler Python sidecars and desktop shell assets.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-$ROOT_DIR/.pyinstaller-cache}"
PYINSTALLER_DIST_DIR="${PYINSTALLER_DIST_DIR:-$ROOT_DIR/dist/pyinstaller}"
PYINSTALLER_WORK_DIR="${PYINSTALLER_WORK_DIR:-$ROOT_DIR/build/pyinstaller}"
TAURI_BIN_DIR="${TAURI_BIN_DIR:-$ROOT_DIR/src-tauri/binaries}"
BUILD_FRONTEND=1
BUILD_PYINSTALLER=1
BUILD_DESKTOP=0
RUN_SMOKE=0
PYINSTALLER_CLEAN=0

usage() {
  cat <<'EOF'
Usage: scripts/package_app.sh [options]

Builds production artifacts for the opportunity crawler:
  1. Vue frontend static assets.
  2. PyInstaller sidecars for control plane, agent, and all-in-one.
  3. Tauri sidecar binaries under src-tauri/binaries with target-triple suffixes.

Options:
  --desktop             Run the Tauri desktop bundle build after sidecars are prepared.
  --verify              Run package smoke tests after building sidecars.
  --clean               Ask PyInstaller to clean its analysis cache before building.
  --skip-frontend       Do not run the Vue frontend build.
  --skip-pyinstaller    Do not run PyInstaller or copy sidecars.
  --help                Show this help.

Environment:
  PYTHON_BIN            Python executable used for PyInstaller and smoke tests.
  PYINSTALLER_CONFIG_DIR Override PyInstaller cache/config directory.
  TAURI_TARGET_TRIPLE   Override auto-detected Tauri sidecar target triple.
  PYINSTALLER_DIST_DIR  Override PyInstaller dist output directory.
  PYINSTALLER_WORK_DIR  Override PyInstaller build work directory.
  TAURI_BIN_DIR         Override Tauri sidecar binary output directory.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --desktop)
      BUILD_DESKTOP=1
      ;;
    --verify)
      RUN_SMOKE=1
      ;;
    --clean)
      PYINSTALLER_CLEAN=1
      ;;
    --skip-frontend)
      BUILD_FRONTEND=0
      ;;
    --skip-pyinstaller)
      BUILD_PYINSTALLER=0
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

log() {
  printf '\n==> %s\n' "$*"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 127
  fi
}

detect_tauri_target_triple() {
  if [[ -n "${TAURI_TARGET_TRIPLE:-}" ]]; then
    printf '%s\n' "$TAURI_TARGET_TRIPLE"
    return
  fi

  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"
  case "$os:$arch" in
    Darwin:arm64|Darwin:aarch64) printf '%s\n' "aarch64-apple-darwin" ;;
    Darwin:x86_64) printf '%s\n' "x86_64-apple-darwin" ;;
    Linux:arm64|Linux:aarch64) printf '%s\n' "aarch64-unknown-linux-gnu" ;;
    Linux:x86_64) printf '%s\n' "x86_64-unknown-linux-gnu" ;;
    MINGW*:x86_64|MSYS*:x86_64|CYGWIN*:x86_64) printf '%s\n' "x86_64-pc-windows-msvc" ;;
    *)
      echo "Unable to detect Tauri target triple for $os/$arch. Set TAURI_TARGET_TRIPLE." >&2
      exit 1
      ;;
  esac
}

run_frontend_build() {
  require_command npm
  log "Building frontend"
  npm --prefix "$ROOT_DIR/frontend" run build
}

run_pyinstaller_builds() {
  log "Checking PyInstaller availability"
  export PYINSTALLER_CONFIG_DIR
  mkdir -p "$PYINSTALLER_CONFIG_DIR"
  "$PYTHON_BIN" -m PyInstaller --version >/dev/null

  local clean_arg=""
  if [[ "$PYINSTALLER_CLEAN" -eq 1 ]]; then
    clean_arg="--clean"
  fi

  local specs=(
    "$ROOT_DIR/packaging/pyinstaller/control_plane.spec"
    "$ROOT_DIR/packaging/pyinstaller/agent.spec"
    "$ROOT_DIR/packaging/pyinstaller/all_in_one.spec"
  )

  for spec in "${specs[@]}"; do
    log "Building $(basename "$spec")"
    "$PYTHON_BIN" -m PyInstaller \
      --noconfirm \
      --distpath "$PYINSTALLER_DIST_DIR" \
      --workpath "$PYINSTALLER_WORK_DIR" \
      ${clean_arg:+"$clean_arg"} \
      "$spec"
  done
}

copy_tauri_sidecars() {
  local target_triple exe_ext
  target_triple="$(detect_tauri_target_triple)"
  exe_ext=""
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) exe_ext=".exe" ;;
  esac

  mkdir -p "$TAURI_BIN_DIR"

  local names=(
    "opportunity-crawler-control-plane"
    "opportunity-crawler-agent"
    "opportunity-crawler-all-in-one"
  )

  for name in "${names[@]}"; do
    local source_path target_path
    source_path="$PYINSTALLER_DIST_DIR/$name/$name$exe_ext"
    target_path="$TAURI_BIN_DIR/$name-$target_triple$exe_ext"
    if [[ ! -x "$source_path" ]]; then
      echo "Expected PyInstaller executable not found: $source_path" >&2
      exit 1
    fi
    log "Copying sidecar $(basename "$target_path")"
    cp "$source_path" "$target_path"
    chmod +x "$target_path"
  done
}

run_smoke_tests() {
  log "Running package smoke tests"
  "$PYTHON_BIN" -m pytest -q tests/smoke
}

run_desktop_build() {
  require_command cargo
  log "Building Tauri desktop bundle"
  (cd "$ROOT_DIR" && cargo tauri build)
}

if [[ "$BUILD_FRONTEND" -eq 1 ]]; then
  run_frontend_build
fi

if [[ "$BUILD_PYINSTALLER" -eq 1 ]]; then
  run_pyinstaller_builds
  copy_tauri_sidecars
fi

if [[ "$RUN_SMOKE" -eq 1 ]]; then
  run_smoke_tests
fi

if [[ "$BUILD_DESKTOP" -eq 1 ]]; then
  run_desktop_build
fi

log "Packaging artifacts are ready"
printf 'PyInstaller dist: %s\n' "$PYINSTALLER_DIST_DIR"
printf 'Tauri sidecars:   %s\n' "$TAURI_BIN_DIR"
if [[ "$BUILD_DESKTOP" -eq 1 ]]; then
  printf 'Desktop bundles:  %s\n' "$ROOT_DIR/src-tauri/target/release/bundle"
fi
