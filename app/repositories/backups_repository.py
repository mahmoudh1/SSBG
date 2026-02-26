from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.backup_metadata import BackupMetadataModel


class BackupsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_metadata(self, record: BackupMetadataModel) -> BackupMetadataModel:
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def get_by_backup_id(self, backup_id: str) -> BackupMetadataModel | None:
        result = await self._session.execute(
            select(BackupMetadataModel).where(BackupMetadataModel.backup_id == backup_id),
        )
        return result.scalar_one_or_none()

    async def update_metadata(
        self,
        backup_id: str,
        **fields: object,
    ) -> BackupMetadataModel | None:
        record = await self.get_by_backup_id(backup_id)
        if record is None:
            return None
        for key, value in fields.items():
            setattr(record, key, value)
        await self._session.commit()
        await self._session.refresh(record)
        return record
