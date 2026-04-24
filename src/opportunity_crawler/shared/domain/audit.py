from __future__ import annotations

from typing import Any


SENSITIVE_KEY_PARTS = ("password", "token", "secret", "cookie", "credential")
PHONE_KEY_PARTS = ("phone", "mobile", "tel")


def mask_audit_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {key: _mask_value(key, value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [mask_audit_payload(item) for item in payload]
    return payload


def _mask_value(key: str, value: Any) -> Any:
    lowered = key.lower()
    if any(part in lowered for part in SENSITIVE_KEY_PARTS):
        return "***"
    if any(part in lowered for part in PHONE_KEY_PARTS) and isinstance(value, str):
        return _mask_phone(value)
    return mask_audit_payload(value)


def _mask_phone(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) >= 7:
        return f"{digits[:3]}****{digits[-4:]}"
    return "***"

