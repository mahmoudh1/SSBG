from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.core.enums import AlertSeverity
from app.schemas.auth import ApiKeyPrincipal
from app.services.monitoring_service import MonitoringRule, MonitoringService


class InMemoryAlertsRepository:
    def __init__(self) -> None:
        self.alerts: list[Any] = []

    async def get_by_dedupe_key(self, dedupe_key: str) -> Any | None:
        for alert in self.alerts:
            if alert.dedupe_key == dedupe_key:
                return alert
        return None

    async def create_alert(self, record: Any) -> Any:
        record.created_at = record.created_at or datetime.now(UTC)
        self.alerts.append(record)
        return record


class FakeAuditService:
    def __init__(self) -> None:
        self.actions: list[dict[str, object]] = []

    async def record_admin_action(
        self,
        actor_key_id: str | None,
        action: str,
        resource: str,
        resource_id: str | None,
        client_ip: str | None,
    ) -> None:
        self.actions.append(
            {
                'actor_key_id': actor_key_id,
                'action': action,
                'resource': resource,
                'resource_id': resource_id,
                'client_ip': client_ip,
            },
        )


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


@pytest.mark.asyncio
async def test_threshold_crossing_creates_alert_with_expected_fields_and_audit() -> None:
    repository = InMemoryAlertsRepository()
    audit = FakeAuditService()
    clock = MutableClock(datetime(2026, 2, 28, 10, 0, tzinfo=UTC))
    service = MonitoringService(
        alerts_repository=repository,
        audit_service=audit,  # type: ignore[arg-type]
        now_provider=clock,
    )
    principal = ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')

    await service.process_security_event('restore_restricted_blocked', principal, 'backup-001')
    await service.process_security_event('restore_restricted_blocked', principal, 'backup-001')
    created = await service.process_security_event(
        'restore_restricted_blocked',
        principal,
        'backup-001',
    )

    assert created is not None
    assert created.rule_id == 'RESTORE_RESTRICTED_SPIKE'
    assert created.severity == AlertSeverity.HIGH.value
    assert created.related_backup_id == 'backup-001'
    assert created.alert_id
    assert audit.actions and audit.actions[-1]['action'] == 'alert_created'


@pytest.mark.asyncio
async def test_no_false_alert_when_threshold_not_crossed() -> None:
    repository = InMemoryAlertsRepository()
    audit = FakeAuditService()
    clock = MutableClock(datetime(2026, 2, 28, 10, 0, tzinfo=UTC))
    service = MonitoringService(
        alerts_repository=repository,
        audit_service=audit,  # type: ignore[arg-type]
        now_provider=clock,
    )
    principal = ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')

    created = await service.process_security_event('restore_failed', principal, 'backup-001')

    assert created is None
    assert repository.alerts == []
    assert audit.actions == []


@pytest.mark.asyncio
async def test_repeated_event_processing_is_idempotent_within_same_window_bucket() -> None:
    repository = InMemoryAlertsRepository()
    audit = FakeAuditService()
    clock = MutableClock(datetime(2026, 2, 28, 10, 0, tzinfo=UTC))
    rules = [
        MonitoringRule(
            rule_id='R1',
            source_event='restore_failed',
            threshold=1,
            window_minutes=10,
            severity=AlertSeverity.MEDIUM,
            reason='test',
        ),
    ]
    service = MonitoringService(
        alerts_repository=repository,
        audit_service=audit,  # type: ignore[arg-type]
        rules=rules,
        now_provider=clock,
    )
    principal = ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')

    first = await service.process_security_event('restore_failed', principal, 'backup-001')
    second = await service.process_security_event('restore_failed', principal, 'backup-001')
    clock.now = clock.now + timedelta(minutes=1)
    third = await service.process_security_event('restore_failed', principal, 'backup-001')

    assert first is not None
    assert second is not None
    assert third is not None
    assert len(repository.alerts) == 1
