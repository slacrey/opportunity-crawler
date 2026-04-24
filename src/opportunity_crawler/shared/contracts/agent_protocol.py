from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ControlPlaneCommandKind(StrEnum):
    START_COLLECTION_RUN = "start_collection_run"
    STOP_COLLECTION_RUN = "stop_collection_run"
    OPEN_SOURCE_SESSION = "open_source_session"
    RELEASE_SOURCE_SESSION = "release_source_session"
    TRIAL_RUN_ADVANCED_RULE = "trial_run_advanced_rule"
    HEALTH_CHECK = "health_check"


class CollectionEventKind(StrEnum):
    REGISTERED = "registered"
    HEARTBEAT = "heartbeat"
    RUN_STARTED = "run_started"
    PAGE_OPENED = "page_opened"
    QUERY_SUBMITTED = "query_submitted"
    PAGE_COLLECTED = "page_collected"
    ITEM_FAILED = "item_failed"
    RUN_SUCCEEDED = "run_succeeded"
    RUN_FAILED = "run_failed"
    LOGIN_REQUIRED = "login_required"
    OPERATOR_INTERVENTION_REQUIRED = "operator_intervention_required"
    RUN_STOPPED = "run_stopped"
    TRIAL_RUN_COMPLETED = "trial_run_completed"
    HEALTH_CHECK_COMPLETED = "health_check_completed"


class RegisterMessage(BaseModel):
    message_type: Literal["register"]
    agent_id: str
    host_id: str
    capacity: int
    hostname: str | None = None
    platform: str | None = None
    app_version: str | None = None


class RegisteredMessage(BaseModel):
    message_type: Literal["registered"] = "registered"
    agent_id: str
    host_id: str


class HeartbeatMessage(BaseModel):
    message_type: Literal["heartbeat"] = "heartbeat"
    agent_id: str


class CollectionCommandMessage(BaseModel):
    message_type: Literal["collection_command"] = "collection_command"
    command: ControlPlaneCommandKind
    command_id: str
    run_id: str | None = None
    source_id: int
    rule_version: int | None = None
    adapter_mode: str | None = None
    login_mode: str | None = None
    source_account_id: int | None = None
    deadline_at: str | None = None
    reason: str | None = None
    draft_rule_payload: dict[str, Any] | None = None
    max_items: int | None = None


class CollectionEventMessage(BaseModel):
    message_type: Literal["collection_event"] = "collection_event"
    event_kind: CollectionEventKind
    command_id: str
    run_id: str | None = None
    source_id: int
    adapter_mode: str | None = None
    page_count: int = 0
    item_count: int = 0
    rows: list[dict[str, Any]] = Field(default_factory=list)
    failure_kind: str | None = None
    detail: str | None = None
    diagnostic_snapshot: dict[str, Any] = Field(default_factory=dict)


AgentInboundMessage = RegisterMessage | HeartbeatMessage | CollectionEventMessage
ControlPlaneMessage = RegisteredMessage | CollectionCommandMessage


def parse_agent_message(payload: object) -> AgentInboundMessage:
    if not isinstance(payload, dict):
        raise ValueError("agent message must be a JSON object")
    message_type = payload.get("message_type")
    if message_type == "register":
        return RegisterMessage.model_validate(payload)
    if message_type == "heartbeat":
        return HeartbeatMessage.model_validate(payload)
    if message_type == "collection_event":
        return CollectionEventMessage.model_validate(payload)
    raise ValueError(f"unsupported agent message_type: {message_type}")


def parse_control_plane_message(payload: object) -> ControlPlaneMessage:
    if not isinstance(payload, dict):
        raise ValueError("control-plane message must be a JSON object")
    message_type = payload.get("message_type")
    if message_type == "registered":
        return RegisteredMessage.model_validate(payload)
    if message_type == "collection_command":
        return CollectionCommandMessage.model_validate(payload)
    raise ValueError(f"unsupported control-plane message_type: {message_type}")

