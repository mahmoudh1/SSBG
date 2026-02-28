from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ApiKeyCreateRequest(BaseModel):
    role: str
    department: str
    description: str | None = None
    expires_at: datetime | None = None
    allowed_ips: list[str] | None = None


class ApiKeyResponse(BaseModel):
    key_id: str
    key_prefix: str
    role: str
    department: str
    description: str | None = None
    created_at: datetime
    expires_at: datetime | None = None
    is_active: bool
    allowed_ips: list[str] | None = None


class ApiKeyCreateResponse(BaseModel):
    api_key: str
    key: ApiKeyResponse


class PolicyCreateRequest(BaseModel):
    name: str
    description: str | None = None
    rule_json: dict[str, object]
    is_active: bool = True


class PolicyUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    rule_json: dict[str, object] | None = None
    is_active: bool | None = None


class PolicyResponse(BaseModel):
    policy_id: str
    name: str
    description: str | None = None
    rule_json: dict[str, object]
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None


class IncidentTransitionRequest(BaseModel):
    level: str
    reason: str | None = None


class IncidentStateResponse(BaseModel):
    level: str
    changed_by_key_id: str | None = None
    reason: str | None = None
    changed_at: datetime | None = None


class AlertResponse(BaseModel):
    alert_id: str
    rule_id: str
    severity: str
    status: str
    source_event: str
    actor_key_id: str | None = None
    related_backup_id: str | None = None
    reason: str
    metadata_json: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class AlertStatusUpdateRequest(BaseModel):
    status: str


class KeyRotationRequest(BaseModel):
    to_version_id: str
    reason: str | None = None


class KeyVersionResponse(BaseModel):
    version_id: str
    is_active: bool
    is_destroyed: bool
    rotated_from_version: str | None = None
    created_by_key_id: str | None = None
    rotation_reason: str | None = None
    created_at: datetime | None = None
    activated_at: datetime | None = None
    destroyed_at: datetime | None = None


class CryptoShredRequest(BaseModel):
    confirmation: str


class CryptoShredResponse(BaseModel):
    version_id: str
    destroyed: bool
    affected_backups: int
    incident_effect: str


class CryptoShredOutcomeResponse(BaseModel):
    version_id: str
    key_destroyed: bool
    destroyed_at: datetime | None = None
    total_backups: int
    irreversible_backups: int
    active_backups: int
    processing_backups: int
    failed_backups: int
    last_shredded_at: datetime | None = None
    irreversible_reason: str | None = None
