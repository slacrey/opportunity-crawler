from __future__ import annotations

from pathlib import Path
from typing import Mapping
import sys

from opportunity_crawler.bootstrap.runtime import RuntimeBundle
from opportunity_crawler.shared.config import AppRole, load_settings


def build_runtime(
    config_path: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> RuntimeBundle:
    settings = load_settings(AppRole.CONTROL_PLANE, config_path=config_path, environ=environ)
    return RuntimeBundle(role=AppRole.CONTROL_PLANE, settings=settings)


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    config_path = args[0] if args else None
    build_runtime(config_path=config_path)


if __name__ == "__main__":
    main()
