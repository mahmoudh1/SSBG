from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.enums import ClassificationLevel


class BackupRequest(BaseModel):
    classification: ClassificationLevel | None = None
    source_system: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=255)
    payload: str | None = Field(default=None, max_length=1000000)
