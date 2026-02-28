from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from hashlib import sha256
from typing import Any, Protocol
from uuid import uuid4

from app.core.enums import AlertSeverity, AlertStatus
from app.infrastructure.db.models.alert import AlertModel
from app.schemas.auth import ApiKeyPrincipal
from app.services.audit_service import AuditService


@dataclass(frozen=True)
class MonitoringRule:
    rule_id: str
    source_event: str
    threshold: int
    window_minutes: int
    severity: AlertSeverity
    reason: str


class AlertsRepositoryLike(Protocol):
    async def get_by_dedupe_key(self, dedupe_key: str) -> AlertModel | None:
        ...

    async def create_alert(self, record: AlertModel) -> AlertModel:
        ...


class MonitoringService:
    def __init__(
        self,
        alerts_repository: AlertsRepositoryLike,
        audit_service: AuditService,
        rules: list[MonitoringRule] | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._alerts_repository = alerts_repository
        self._audit_service = audit_service
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self._rules = rules or [
            MonitoringRule(
                rule_id='RESTORE_RESTRICTED_SPIKE',
                source_event='restore_restricted_blocked',
                threshold=3,
                window_minutes=10,
                severity=AlertSeverity.HIGH,
                reason='Repeated restore restrictions detected',
            ),
            MonitoringRule(
                rule_id='RESTORE_FAILURE_SPIKE',
                source_event='restore_failed',
                threshold=3,
                window_minutes=10,
                severity=AlertSeverity.MEDIUM,
                reason='Repeated restore failures detected',
            ),
        ]
        self._event_counters: dict[str, list[datetime]] = {}

    def _counter_key(self, rule_id: str, actor_key_id: str | None) -> str:
        return f'{rule_id}:{actor_key_id or "anonymous"}'

    def _dedupe_key(self, rule_id: str, actor_key_id: str | None, window_bucket: str) -> str:
        base = f'{rule_id}:{actor_key_id or "anonymous"}:{window_bucket}'
        return sha256(base.encode()).hexdigest()

    @staticmethod
    def _window_bucket(now: datetime, window_minutes: int) -> str:
        now_utc = now.astimezone(UTC)
        minute_bucket = (now_utc.minute // window_minutes) * window_minutes
        bucket = now_utc.replace(minute=minute_bucket, second=0, microsecond=0)
        return bucket.isoformat()

    async def _event_count(
        self,
        rule_id: str,
        source_event: str,
        actor_key_id: str | None,
        window_minutes: int,
        now: datetime,
    ) -> int:
        since = now - timedelta(minutes=window_minutes)
        counter: Any = getattr(self._audit_service, 'count_security_events', None)
        if callable(counter):
            return int(await counter(source_event, actor_key_id, since))
        counter_key = self._counter_key(rule_id, actor_key_id)
        window_seconds = window_minutes * 60
        history = [
            timestamp
            for timestamp in self._event_counters.get(counter_key, [])
            if (now - timestamp).total_seconds() <= window_seconds
        ]
        history.append(now)
        self._event_counters[counter_key] = history
        return len(history)

    async def process_security_event(
        self,
        source_event: str,
        actor: ApiKeyPrincipal | None,
        backup_id: str | None,
        metadata: dict[str, object] | None = None,
    ) -> AlertModel | None:
        now = self._now_provider()
        actor_key_id = actor.key_id if actor else None
        matched_rule = next(
            (rule for rule in self._rules if rule.source_event == source_event),
            None,
        )
        if matched_rule is None:
            return None

        count = await self._event_count(
            rule_id=matched_rule.rule_id,
            source_event=matched_rule.source_event,
            actor_key_id=actor_key_id,
            window_minutes=matched_rule.window_minutes,
            now=now,
        )
        if count < matched_rule.threshold:
            return None

        window_bucket = self._window_bucket(now, matched_rule.window_minutes)
        dedupe_key = self._dedupe_key(matched_rule.rule_id, actor_key_id, window_bucket)
        existing = await self._alerts_repository.get_by_dedupe_key(dedupe_key)
        if existing is not None:
            return existing

        alert = AlertModel(
            alert_id=uuid4().hex,
            rule_id=matched_rule.rule_id,
            severity=matched_rule.severity.value,
            status=AlertStatus.OPEN.value,
            source_event=source_event,
            actor_key_id=actor_key_id,
            related_backup_id=backup_id,
            reason=matched_rule.reason,
            metadata_json=json.dumps(metadata or {}, sort_keys=True),
            dedupe_key=dedupe_key,
        )
        created = await self._alerts_repository.create_alert(alert)
        await self._audit_service.record_admin_action(
            actor_key_id=actor_key_id,
            action='alert_created',
            resource='alert',
            resource_id=created.alert_id,
            client_ip=None,
        )
        return created
