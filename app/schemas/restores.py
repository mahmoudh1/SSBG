from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RestoreRequest(BaseModel):
    backup_id: str = Field(min_length=8, max_length=64)
    reason: str | None = Field(default=None, max_length=255)


class RestoreMetadataSummary(BaseModel):
    backup_id: str
    classification: str
    source_system: str
    status: str
    key_version: str | None = None
    created_at: datetime | None = None
