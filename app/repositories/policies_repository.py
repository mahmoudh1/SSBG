from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.policy_record import PolicyRecordModel


class PoliciesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_policy(self, policy: PolicyRecordModel) -> PolicyRecordModel:
        self._session.add(policy)
        await self._session.commit()
        await self._session.refresh(policy)
        return policy

    async def list_policies(self) -> list[PolicyRecordModel]:
        result = await self._session.execute(
            select(PolicyRecordModel).order_by(PolicyRecordModel.created_at.desc()),
        )
        return list(result.scalars().all())

    async def update_policy(
        self,
        policy_id: str,
        name: str | None,
        description: str | None,
        rule_json: dict[str, object] | None,
        is_active: bool | None,
    ) -> PolicyRecordModel | None:
        result = await self._session.execute(
            select(PolicyRecordModel).where(PolicyRecordModel.policy_id == policy_id),
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        if name is not None:
            record.name = name
        if description is not None:
            record.description = description
        if rule_json is not None:
            record.rule_json = rule_json
        if is_active is not None:
            record.is_active = is_active
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record
