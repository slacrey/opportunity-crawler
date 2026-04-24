from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_crawler.shared.domain.audit import mask_audit_payload


def test_mask_audit_payload_masks_credentials_and_contact_values() -> None:
    masked = mask_audit_payload(
        {
            "credential_profile_id": "cred-local-1",
            "password": "secret-password",
            "api_token": "token-value",
            "contact_phone": "13800000000",
            "nested": {"cookie": "session-cookie", "title": "保留标题"},
        }
    )

    assert masked["credential_profile_id"] == "***"
    assert masked["password"] == "***"
    assert masked["api_token"] == "***"
    assert masked["contact_phone"] == "138****0000"
    assert masked["nested"]["cookie"] == "***"
    assert masked["nested"]["title"] == "保留标题"
