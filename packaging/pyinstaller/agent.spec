# -*- mode: python ; coding: utf-8 -*-

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

SPEC_ROOT = Path(SPECPATH)
PROJECT_ROOT = SPEC_ROOT.parents[1]


def load_common_module():
    common_path = SPEC_ROOT / "common.py"
    spec = importlib.util.spec_from_file_location(
        "opportunity_crawler_pyinstaller_common",
        common_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load packaging common helper from {common_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


common = load_common_module()
entrypoint = PROJECT_ROOT / "packaging" / "pyinstaller" / "entrypoints" / "agent_main.py"

a = Analysis(
    [str(entrypoint)],
    pathex=[str(PROJECT_ROOT), str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=common.pyinstaller_datas(),
    hiddenimports=common.pyinstaller_hiddenimports(),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="opportunity-crawler-agent",
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="opportunity-crawler-agent",
)

