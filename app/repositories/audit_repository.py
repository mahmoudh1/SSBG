from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.audit_log_entry import AuditLogEntryModel


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_entry(self, record: AuditLogEntryModel) -> AuditLogEntryModel:
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record
