from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_auth_service, get_restore_service
from app.core.enums import IncidentLevel
from app.main import create_app
from app.schemas.auth import ApiKeyPrincipal
from app.services.incident_service import IncidentService
from app.services.restore_service import RestoreService


class FakeBackupsRepository:
    def __init__(self) -> None:
        self.metadata = SimpleNamespace(
            backup_id='backup-0001',
            classification='CONFIDENTIAL',
            source_system='system-a',
            status='ACTIVE',
            key_version='P-001',
            created_at=datetime(2026, 2, 28, tzinfo=UTC),
        )

    async def get_by_backup_id(self, backup_id: str) -> object | None:
        return self.metadata if backup_id == self.metadata.backup_id else None


class FakeAuditService:
    def __init__(self) -> None:
        self.restore_events: list[dict[str, object]] = []

    async def record_mfa_outcome(
        self,
        key_id: str | None,
        outcome: str,
        reason: str | None,
        client_ip: str | None,
    ) -> None:
        _ = (key_id, outcome, reason, client_ip)

    async def record_policy_decision(
        self,
        key_id: str | None,
        operation: str,
        allowed: bool,
        reason: str,
        reason_category: str,
        classification: str | None,
        client_ip: str | None,
    ) -> None:
        _ = (key_id, operation, allowed, reason, reason_category, classification, client_ip)

    async def record_restore_event(
        self,
        action: str,
        backup_id: str,
        actor_key_id: str | None,
        actor_role: str | None,
        status: str,
        reason: str | None,
    ) -> None:
        self.restore_events.append(
            {
                'action': action,
                'backup_id': backup_id,
                'actor_key_id': actor_key_id,
                'actor_role': actor_role,
                'status': status,
                'reason': reason,
            },
        )


class FakePolicyService:
    def evaluate_restore(self, principal: ApiKeyPrincipal | None, classification: object) -> Any:
        _ = classification
        return SimpleNamespace(
            allowed=True,
            reason='Restore allowed',
            reason_category='allowed',
            role=principal.role if principal else 'unknown',
        )


class FakeRequestAndMfaAuthService:
    async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
        _ = (raw_key, client_ip)
        return ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')

    async def validate_mfa_token(
        self,
        principal: ApiKeyPrincipal | None,
        mfa_token: str | None,
        client_ip: str | None,
    ) -> None:
        _ = client_ip
        if principal is None or mfa_token != f'mfa:{principal.key_id}':
            from app.services.auth_service import MfaFailure

            raise MfaFailure('MFA_INVALID', 'Invalid MFA token')


class InMemoryIncidentRepository:
    def __init__(self) -> None:
        self.records: list[Any] = []

    async def get_latest(self) -> Any | None:
        return self.records[-1] if self.records else None

    async def append_transition(self, record: Any) -> Any:
        if getattr(record, 'changed_at', None) is None:
            record.changed_at = datetime.now(UTC)
        self.records.append(record)
        return record


def _build_restore_service(
    incident_service: IncidentService,
    audit: FakeAuditService,
) -> RestoreService:
    return RestoreService(  # type: ignore[arg-type]
        FakeBackupsRepository(),
        FakeRequestAndMfaAuthService(),  # type: ignore[arg-type]
        FakePolicyService(),  # type: ignore[arg-type]
        audit,  # type: ignore[arg-type]
        incident_service,  # type: ignore[arg-type]
    )


def _configure_app(
    incident_service: IncidentService,
    audit: FakeAuditService,
) -> FastAPI:
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: FakeRequestAndMfaAuthService()
    app.dependency_overrides[get_restore_service] = lambda: _build_restore_service(
        incident_service,
        audit,
    )
    return app


def test_incident_level_changes_are_enforced_on_subsequent_restore_requests() -> None:
    repository = InMemoryIncidentRepository()
    incident_service = IncidentService(SimpleNamespace(current_incident_level='NORMAL'), repository)  # type: ignore[arg-type]
    audit = FakeAuditService()
    app = _configure_app(incident_service, audit)
    client = TestClient(app)

    normal = client.post(
        '/api/v1/restores',
        json={'backup_id': 'backup-0001'},
        headers={'X-API-Key': 'valid', 'X-MFA-Token': 'mfa:admin-key'},
    )
    assert normal.status_code == 200
    assert normal.json()['data']['status'] == 'metadata_loaded'

    import asyncio

    asyncio.run(
        incident_service.transition_to(
            IncidentLevel.QUARANTINE,
            'admin-key',
            'investigation',
        ),
    )
    quarantine = client.post(
        '/api/v1/restores',
        json={'backup_id': 'backup-0001'},
        headers={'X-API-Key': 'valid', 'X-MFA-Token': 'mfa:admin-key'},
    )
    assert quarantine.status_code == 200
    assert quarantine.json()['data']['status'] == 'pending_manual_review'
    assert quarantine.json()['data']['restriction_reason'] == 'incident_quarantine'

    asyncio.run(incident_service.transition_to(IncidentLevel.LOCKDOWN, 'admin-key', 'critical'))
    lockdown = client.post(
        '/api/v1/restores',
        json={'backup_id': 'backup-0001'},
        headers={'X-API-Key': 'valid', 'X-MFA-Token': 'mfa:admin-key'},
    )
    assert lockdown.status_code == 403
    assert lockdown.json()['error']['code'] == 'RESTORE_RESTRICTED'
    assert lockdown.json()['data']['details'][0]['reason_category'] == 'incident_lockdown'


def test_unknown_incident_state_fails_secure_with_visible_reason_and_audit() -> None:
    repository = InMemoryIncidentRepository()
    repository.records.append(
        SimpleNamespace(
            level='BROKEN',
            changed_by_key_id='admin-key',
            reason='bad-state',
            changed_at=datetime.now(UTC),
        ),
    )
    incident_service = IncidentService(SimpleNamespace(current_incident_level='NORMAL'), repository)  # type: ignore[arg-type]
    audit = FakeAuditService()
    app = _configure_app(incident_service, audit)
    client = TestClient(app)

    response = client.post(
        '/api/v1/restores',
        json={'backup_id': 'backup-0001'},
        headers={'X-API-Key': 'valid', 'X-MFA-Token': 'mfa:admin-key'},
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload['error']['code'] == 'RESTORE_RESTRICTED'
    assert payload['data']['details'][0]['reason_category'] == 'incident_state_unavailable'
    assert audit.restore_events
    assert audit.restore_events[-1]['reason'] == 'incident_state_unavailable'
