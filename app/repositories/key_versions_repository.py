from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.key_version import KeyVersionModel


class KeyVersionsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def get_active(self) -> KeyVersionModel | None:
        result = await self._session.execute(
            select(KeyVersionModel)
            .where(KeyVersionModel.is_active.is_(True))
            .order_by(KeyVersionModel.activated_at.desc(), KeyVersionModel.created_at.desc()),
        )
        return result.scalars().first()

    async def get_by_version_id(self, version_id: str) -> KeyVersionModel | None:
        result = await self._session.execute(
            select(KeyVersionModel).where(KeyVersionModel.version_id == version_id),
        )
        return result.scalar_one_or_none()

    async def list_versions(self) -> list[KeyVersionModel]:
        result = await self._session.execute(
            select(KeyVersionModel).order_by(KeyVersionModel.created_at.desc()),
        )
        return list(result.scalars())

    async def create_version(self, record: KeyVersionModel) -> KeyVersionModel:
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def set_active(
        self,
        to_version_id: str,
        rotated_from_version: str | None,
        reason: str | None,
        actor_key_id: str | None,
    ) -> KeyVersionModel | None:
        record = await self.get_by_version_id(to_version_id)
        if record is None:
            return None
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            select(KeyVersionModel).where(KeyVersionModel.is_active.is_(True)),
        )
        for active in result.scalars():
            active.is_active = False
        record.is_active = True
        record.rotated_from_version = rotated_from_version
        record.rotation_reason = reason
        record.created_by_key_id = actor_key_id
        record.activated_at = now
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def mark_destroyed(
        self,
        version_id: str,
        *,
        destroyed_at: datetime | None = None,
        commit: bool = True,
    ) -> KeyVersionModel | None:
        record = await self.get_by_version_id(version_id)
        if record is None:
            return None
        record.is_destroyed = True
        record.is_active = False
        record.destroyed_at = destroyed_at or datetime.now(timezone.utc)
        if commit:
            await self._session.commit()
            await self._session.refresh(record)
        else:
            await self._session.flush()
        return record
