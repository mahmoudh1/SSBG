from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.core.config import Settings
from app.core.enums import IncidentLevel
from app.infrastructure.db.models.incident_state import IncidentStateModel


class InvalidIncidentTransition(Exception):
    def __init__(self, message: str, reason_category: str) -> None:
        super().__init__(message)
        self.message = message
        self.reason_category = reason_category


@dataclass(frozen=True)
class IncidentStateSnapshot:
    level: IncidentLevel
    changed_by_key_id: str | None
    reason: str | None
    changed_at: datetime | None


class IncidentRepositoryLike(Protocol):
    async def get_latest(self) -> IncidentStateModel | None:
        ...

    async def append_transition(self, record: IncidentStateModel) -> IncidentStateModel:
        ...


class IncidentService:
    def __init__(self, settings: Settings, repository: IncidentRepositoryLike) -> None:
        self._settings = settings
        self._repository = repository
        self._allowed_transitions: dict[IncidentLevel, set[IncidentLevel]] = {
            IncidentLevel.NORMAL: {IncidentLevel.QUARANTINE, IncidentLevel.LOCKDOWN},
            IncidentLevel.QUARANTINE: {IncidentLevel.NORMAL, IncidentLevel.LOCKDOWN},
            IncidentLevel.LOCKDOWN: {IncidentLevel.QUARANTINE},
        }

    async def get_state(self) -> IncidentStateSnapshot:
        latest = await self._repository.get_latest()
        if latest is None:
            try:
                level = IncidentLevel(self._settings.current_incident_level)
            except ValueError:
                level = IncidentLevel.NORMAL
            return IncidentStateSnapshot(
                level=level,
                changed_by_key_id=None,
                reason='default_config',
                changed_at=None,
            )
        try:
            level = IncidentLevel(latest.level)
        except ValueError:
            raise InvalidIncidentTransition(
                'Unknown persisted incident level',
                'invalid_persisted_state',
            ) from None
        return IncidentStateSnapshot(
            level=level,
            changed_by_key_id=latest.changed_by_key_id,
            reason=latest.reason,
            changed_at=latest.changed_at,
        )

    async def get_current_level(self) -> IncidentLevel:
        return (await self.get_state()).level

    async def transition_to(
        self,
        new_level: IncidentLevel,
        changed_by_key_id: str | None,
        reason: str | None,
    ) -> IncidentStateSnapshot:
        current = await self.get_state()
        if current.level == new_level:
            raise InvalidIncidentTransition(
                'Incident level already active',
                'no_state_change',
            )
        allowed = self._allowed_transitions.get(current.level, set())
        if new_level not in allowed:
            raise InvalidIncidentTransition(
                'Incident transition not allowed',
                'invalid_transition',
            )
        record = IncidentStateModel(
            level=new_level.value,
            changed_by_key_id=changed_by_key_id,
            reason=reason,
        )
        persisted = await self._repository.append_transition(record)
        return IncidentStateSnapshot(
            level=new_level,
            changed_by_key_id=persisted.changed_by_key_id,
            reason=persisted.reason,
            changed_at=persisted.changed_at,
        )
