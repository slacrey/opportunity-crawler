from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.control_plane.routes.api.errors import api_error


def test_api_error_payload_shape_is_stable() -> None:
    response = api_error(
        "validation_error",
        "Invalid input",
        status_code=422,
        details=[{"field": "name", "message": "Field required"}],
    )

    assert response.status_code == 422
    assert response.body
    assert response.media_type == "application/json"

