from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AuditChainFailure(BaseModel):
    chain_index: int | None = None
    event_id: str | None = None
    reason: str


class AuditChainValidationResult(BaseModel):
    valid: bool
    checked_entries: int
    failure: AuditChainFailure | None = None


class AuditEntrySummary(BaseModel):
    chain_index: int
    event_id: str
    action: str
    resource: str
    resource_id: str | None = None
    actor_key_id: str | None = None
    actor_role: str | None = None
    status: str | None = None
    reason: str | None = None
    created_at: datetime | None = None
