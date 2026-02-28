from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.incident_state import IncidentStateModel


class IncidentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest(self) -> IncidentStateModel | None:
        result = await self._session.execute(
            select(IncidentStateModel).order_by(
                IncidentStateModel.changed_at.desc(),
                IncidentStateModel.id.desc(),
            ),
        )
        return result.scalars().first()

    async def append_transition(self, record: IncidentStateModel) -> IncidentStateModel:
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record
