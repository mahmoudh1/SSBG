from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.api_key import ApiKeyModel


class ApiKeysRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_hash(self, key_hash: str) -> ApiKeyModel | None:
        result = await self._session.execute(
            select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash),
        )
        return result.scalar_one_or_none()

    async def update_last_used(self, api_key: ApiKeyModel, ip_address: str | None) -> None:
        api_key.last_used_at = datetime.now(timezone.utc)
        api_key.last_used_ip = ip_address
        self._session.add(api_key)
        await self._session.commit()

    async def create_key(self, api_key: ApiKeyModel) -> ApiKeyModel:
        self._session.add(api_key)
        await self._session.commit()
        await self._session.refresh(api_key)
        return api_key

    async def list_keys(self) -> list[ApiKeyModel]:
        result = await self._session.execute(
            select(ApiKeyModel).order_by(ApiKeyModel.created_at.desc()),
        )
        return list(result.scalars().all())

    async def revoke_key(self, key_id: str) -> ApiKeyModel | None:
        result = await self._session.execute(
            select(ApiKeyModel).where(ApiKeyModel.key_id == key_id),
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        record.is_active = False
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record
