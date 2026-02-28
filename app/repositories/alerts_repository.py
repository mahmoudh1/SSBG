from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.alert import AlertModel


class AlertsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_alert(self, record: AlertModel) -> AlertModel:
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def get_by_dedupe_key(self, dedupe_key: str) -> AlertModel | None:
        result = await self._session.execute(
            select(AlertModel).where(AlertModel.dedupe_key == dedupe_key),
        )
        return result.scalar_one_or_none()

    async def get_by_alert_id(self, alert_id: str) -> AlertModel | None:
        result = await self._session.execute(
            select(AlertModel).where(AlertModel.alert_id == alert_id),
        )
        return result.scalar_one_or_none()

    async def list_alerts(
        self,
        offset: int = 0,
        limit: int = 100,
        status: str | None = None,
        severity: str | None = None,
        rule_id: str | None = None,
    ) -> list[AlertModel]:
        query = select(AlertModel)
        if status:
            query = query.where(AlertModel.status == status)
        if severity:
            query = query.where(AlertModel.severity == severity)
        if rule_id:
            query = query.where(AlertModel.rule_id == rule_id)
        result = await self._session.execute(
            query.order_by(AlertModel.created_at.desc()).offset(offset).limit(limit),
        )
        return list(result.scalars())

    async def update_status(self, alert_id: str, status: str) -> AlertModel | None:
        record = await self.get_by_alert_id(alert_id)
        if record is None:
            return None
        record.status = status
        await self._session.commit()
        await self._session.refresh(record)
        return record
