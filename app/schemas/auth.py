from __future__ import annotations

from pydantic import BaseModel


class ApiKeyPrincipal(BaseModel):
    key_id: str
    role: str
    department: str
