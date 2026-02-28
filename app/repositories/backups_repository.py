from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.backup_metadata import BackupMetadataModel


class BackupsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

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

    async def mark_irreversible_by_key_version(
        self,
        key_version: str,
        reason: str,
        *,
        shredded_at: datetime | None = None,
        commit: bool = True,
    ) -> int:
        result = await self._session.execute(
            select(BackupMetadataModel).where(BackupMetadataModel.key_version == key_version),
        )
        records = list(result.scalars())
        event_time = shredded_at or datetime.now(timezone.utc)
        for record in records:
            record.status = 'IRREVERSIBLE'
            record.irreversible_reason = reason
            record.shredded_at = event_time
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        return len(records)

    async def summarize_by_key_version(self, key_version: str) -> dict[str, object]:
        result = await self._session.execute(
            select(BackupMetadataModel).where(BackupMetadataModel.key_version == key_version),
        )
        records = list(result.scalars())
        total_backups = len(records)
        irreversible_records = [record for record in records if record.status == 'IRREVERSIBLE']
        latest_shredded = None
        if irreversible_records:
            latest_shredded = max(
                (record.shredded_at for record in irreversible_records if record.shredded_at),
                default=None,
            )
        return {
            'total_backups': total_backups,
            'irreversible_backups': len(irreversible_records),
            'active_backups': sum(1 for record in records if record.status == 'ACTIVE'),
            'processing_backups': sum(1 for record in records if record.status == 'PROCESSING'),
            'failed_backups': sum(1 for record in records if record.status == 'FAILED'),
            'last_shredded_at': latest_shredded,
            'irreversible_reason': (
                irreversible_records[0].irreversible_reason if irreversible_records else None
            ),
        }
