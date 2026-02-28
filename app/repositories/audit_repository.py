from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
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

    async def count_entries(
        self,
        action: str,
        resource: str,
        actor_key_id: str | None,
        since: datetime,
    ) -> int:
        query = select(func.count()).select_from(AuditLogEntryModel).where(
            AuditLogEntryModel.action == action,
            AuditLogEntryModel.resource == resource,
            AuditLogEntryModel.created_at >= since,
        )
        if actor_key_id is None:
            query = query.where(AuditLogEntryModel.actor_key_id.is_(None))
        else:
            query = query.where(AuditLogEntryModel.actor_key_id == actor_key_id)
        result = await self._session.execute(query)
        return int(result.scalar_one())
