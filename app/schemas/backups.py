from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class BackupClassification(str, Enum):
    public = 'PUBLIC'
    internal = 'INTERNAL'
    confidential = 'CONFIDENTIAL'
    secret = 'SECRET'


class BackupRequest(BaseModel):
    classification: BackupClassification
    source_system: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=255)
