from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.audit_log_entry import AuditLogEntryModel


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_entry(self, record: AuditLogEntryModel) -> AuditLogEntryModel:
        self._session.add(record)
        try:
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
        await self._session.refresh(record)
        return record

    async def get_latest_chain_cursor(self) -> tuple[int, str] | None:
        result = await self._session.execute(
            select(AuditLogEntryModel.chain_index, AuditLogEntryModel.entry_hash).order_by(
                AuditLogEntryModel.chain_index.desc(),
            ),
        )
        latest = result.first()
        if latest is None:
            return None
        return int(latest[0]), str(latest[1])

    async def list_entries(
        self,
        offset: int = 0,
        limit: int = 100,
        action: str | None = None,
        resource: str | None = None,
        status: str | None = None,
    ) -> list[AuditLogEntryModel]:
        query = select(AuditLogEntryModel)
        if action:
            query = query.where(AuditLogEntryModel.action == action)
        if resource:
            query = query.where(AuditLogEntryModel.resource == resource)
        if status:
            query = query.where(AuditLogEntryModel.status == status)
        result = await self._session.execute(
            query.order_by(AuditLogEntryModel.chain_index.asc()).offset(offset).limit(limit),
        )
        return list(result.scalars())
