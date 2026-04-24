from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_tauri_config_uses_static_vue_dist_and_named_sidecars() -> None:
    config = json.loads((ROOT / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))

    assert config["build"]["frontendDist"] == "../frontend/dist"
    assert config["build"]["beforeBuildCommand"] == "npm --prefix frontend run build"
    assert set(config["bundle"]["externalBin"]) == {
        "binaries/opportunity-crawler-control-plane",
        "binaries/opportunity-crawler-agent",
        "binaries/opportunity-crawler-all-in-one",
    }


def test_tauri_capability_allows_only_named_sidecars_with_config_argument() -> None:
    capability = json.loads((ROOT / "src-tauri" / "capabilities" / "default.json").read_text(encoding="utf-8"))

    serialized = json.dumps(capability, ensure_ascii=False)
    assert "shell:allow-execute" in serialized
    assert '"sidecar": true' in serialized
    assert "opportunity-crawler-all-in-one" in serialized
    assert "--config" in serialized
    assert '"*"' not in serialized
    assert "shell:allow-open" not in serialized


def test_tauri_icon_is_valid_512_rgba_png() -> None:
    png = (ROOT / "src-tauri" / "icons" / "icon.png").read_bytes()
    assert png.startswith(b"\x89PNG\r\n\x1a\n")

    offset = 8
    width = height = color_type = None
    compressed = b""
    while offset < len(png):
        length = struct.unpack(">I", png[offset : offset + 4])[0]
        kind = png[offset + 4 : offset + 8]
        payload = png[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, *_ = struct.unpack(">IIBBBBB", payload)
            assert bit_depth == 8
        elif kind == b"IDAT":
            compressed += payload
        elif kind == b"IEND":
            break

    assert (width, height, color_type) == (512, 512, 6)
    raw = zlib.decompress(compressed)
    assert len(raw) == 512 * (1 + 512 * 4)
