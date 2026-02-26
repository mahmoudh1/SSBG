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
