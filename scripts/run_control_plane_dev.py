from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.bootstrap.control_plane import build_runtime


if __name__ == "__main__":
    build_runtime(config_path=ROOT / "packaging" / "defaults" / "control_plane.toml")

