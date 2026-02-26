from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_auth_service, get_restore_service
from app.core.enums import IncidentLevel
from app.main import create_app
from app.schemas.auth import ApiKeyPrincipal
from app.services.restore_service import RestoreService


class FakeBackupsRepository:
    def __init__(self, metadata: object | None) -> None:
        self.metadata = metadata

    async def get_by_backup_id(self, backup_id: str) -> object | None:
        if self.metadata is None:
            return None
        return self.metadata if getattr(self.metadata, 'backup_id', None) == backup_id else None


class FakeAuditService:
    def __init__(self) -> None:
        self.mfa_events: list[dict[str, Any]] = []
        self.policy_events: list[dict[str, Any]] = []
        self.restore_events: list[dict[str, Any]] = []

    async def record_mfa_outcome(
        self,
        key_id: str | None,
        outcome: str,
        reason: str | None,
        client_ip: str | None,
    ) -> None:
        self.mfa_events.append(
            {'key_id': key_id, 'outcome': outcome, 'reason': reason, 'client_ip': client_ip},
        )

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
        self.policy_events.append(
            {
                'key_id': key_id,
                'operation': operation,
                'allowed': allowed,
                'reason': reason,
                'reason_category': reason_category,
                'classification': classification,
                'client_ip': client_ip,
            },
        )

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


class FakeAuthService:
    def __init__(self, audit: FakeAuditService) -> None:
        self._audit = audit

    async def validate_mfa_token(
        self,
        principal: ApiKeyPrincipal | None,
        mfa_token: str | None,
        client_ip: str | None,
    ) -> None:
        if principal is None or not mfa_token:
            await self._audit.record_mfa_outcome(
                key_id=principal.key_id if principal else None,
                outcome='denied',
                reason='missing_mfa',
                client_ip=client_ip,
            )
            from app.services.auth_service import MfaFailure

            raise MfaFailure('MFA_REQUIRED', 'MFA token required')
        if mfa_token != f'mfa:{principal.key_id}':
            await self._audit.record_mfa_outcome(
                key_id=principal.key_id,
                outcome='denied',
                reason='invalid_mfa',
                client_ip=client_ip,
            )
            from app.services.auth_service import MfaFailure

            raise MfaFailure('MFA_INVALID', 'Invalid MFA token')
        await self._audit.record_mfa_outcome(
            key_id=principal.key_id,
            outcome='allowed',
            reason=None,
            client_ip=client_ip,
        )


class FakePolicyServiceAllow:
    def evaluate_restore(self, principal: ApiKeyPrincipal | None, classification: object) -> Any:
        return SimpleNamespace(
            allowed=True,
            reason='Restore allowed',
            reason_category='allowed',
            role=principal.role if principal else 'unknown',
            classification=classification,
        )


class FakePolicyServiceDeny:
    def evaluate_restore(self, principal: ApiKeyPrincipal | None, classification: object) -> Any:
        return SimpleNamespace(
            allowed=False,
            reason='Restore policy denied',
            reason_category='policy_rule',
            role=principal.role if principal else 'unknown',
            classification=classification,
        )


class FakeIncidentService:
    def __init__(self, level: IncidentLevel = IncidentLevel.NORMAL) -> None:
        self._level = level

    def get_current_level(self) -> IncidentLevel:
        return self._level


def _override_restore_auth(app: FastAPI) -> None:
    class _AuthForRequestPipeline:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            return ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')

    app.dependency_overrides[get_auth_service] = lambda: _AuthForRequestPipeline()


def _build_restore_service(
    policy_service: object,
    audit: FakeAuditService,
    incident_service: object | None = None,
) -> RestoreService:
    metadata = SimpleNamespace(
        backup_id='backup-0001',
        classification='CONFIDENTIAL',
        source_system='system-a',
        status='ACTIVE',
        key_version='P-001',
        created_at=datetime(2026, 2, 26, tzinfo=timezone.utc),
    )
    return RestoreService(  # type: ignore[arg-type]
        FakeBackupsRepository(metadata),
        FakeAuthService(audit),  # type: ignore[arg-type]
        policy_service,  # type: ignore[arg-type]
        audit,  # type: ignore[arg-type]
        incident_service or FakeIncidentService(),  # type: ignore[arg-type]
    )


def test_restore_missing_mfa_denied() -> None:
    app = create_app()
    _override_restore_auth(app)
    audit = FakeAuditService()
    app.dependency_overrides[get_restore_service] = lambda: _build_restore_service(
        FakePolicyServiceAllow(),
        audit,
    )
    client = TestClient(app)

    response = client.post(
        '/api/v1/restores',
        json={'backup_id': 'backup-0001'},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 401
    assert response.json()['error']['code'] == 'MFA_REQUIRED'
    assert audit.mfa_events and audit.mfa_events[0]['outcome'] == 'denied'


def test_restore_missing_mfa_denied_before_metadata_existence_checks() -> None:
    app = create_app()
    _override_restore_auth(app)
    audit = FakeAuditService()
    app.dependency_overrides[get_restore_service] = lambda: _build_restore_service(
        FakePolicyServiceAllow(),
        audit,
    )
    client = TestClient(app)

    response = client.post(
        '/api/v1/restores',
        json={'backup_id': 'backup-does-not-exist'},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 401
    assert response.json()['error']['code'] == 'MFA_REQUIRED'


def test_restore_invalid_mfa_denied_and_audited() -> None:
    app = create_app()
    _override_restore_auth(app)
    audit = FakeAuditService()
    app.dependency_overrides[get_restore_service] = lambda: _build_restore_service(
        FakePolicyServiceAllow(),
        audit,
    )
    client = TestClient(app)

    response = client.post(
        '/api/v1/restores',
        json={'backup_id': 'backup-0001'},
        headers={'X-API-Key': 'valid', 'X-MFA-Token': 'invalid'},
    )

    assert response.status_code == 401
    assert response.json()['error']['code'] == 'MFA_INVALID'
    assert audit.mfa_events and audit.mfa_events[0]['reason'] == 'invalid_mfa'


def test_restore_valid_auth_mfa_and_policy_allows_continuation() -> None:
    app = create_app()
    _override_restore_auth(app)
    audit = FakeAuditService()
    app.dependency_overrides[get_restore_service] = lambda: _build_restore_service(
        FakePolicyServiceAllow(),
        audit,
    )
    client = TestClient(app)

    response = client.post(
        '/api/v1/restores',
        json={'backup_id': 'backup-0001'},
        headers={'X-API-Key': 'valid', 'X-MFA-Token': 'mfa:admin-key'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['data']['status'] == 'metadata_loaded'
    assert payload['data']['next_step'] == 'mfa_policy_authorization'
    assert audit.mfa_events and audit.mfa_events[-1]['outcome'] == 'allowed'
    assert audit.policy_events and audit.policy_events[-1]['allowed'] is True


def test_restore_policy_deny_returns_documented_error() -> None:
    app = create_app()
    _override_restore_auth(app)
    audit = FakeAuditService()
    app.dependency_overrides[get_restore_service] = lambda: _build_restore_service(
        FakePolicyServiceDeny(),
        audit,
    )
    client = TestClient(app)

    response = client.post(
        '/api/v1/restores',
        json={'backup_id': 'backup-0001'},
        headers={'X-API-Key': 'valid', 'X-MFA-Token': 'mfa:admin-key'},
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload['error']['code'] == 'POLICY_DENIED'
    assert payload['data']['details'][0]['reason_category'] == 'policy_rule'
    assert audit.policy_events and audit.policy_events[-1]['allowed'] is False


def test_restore_quarantine_incident_returns_pending_manual_review_and_audit_reason() -> None:
    app = create_app()
    _override_restore_auth(app)
    audit = FakeAuditService()
    app.dependency_overrides[get_restore_service] = lambda: _build_restore_service(
        FakePolicyServiceAllow(),
        audit,
        FakeIncidentService(IncidentLevel.QUARANTINE),
    )
    client = TestClient(app)

    response = client.post(
        '/api/v1/restores',
        json={'backup_id': 'backup-0001'},
        headers={'X-API-Key': 'valid', 'X-MFA-Token': 'mfa:admin-key'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['data']['status'] == 'pending_manual_review'
    assert payload['data']['restriction_reason'] == 'incident_quarantine'
    assert 'restore_token' not in payload['data']
    assert audit.restore_events and audit.restore_events[-1]['reason'] == 'incident_quarantine'


def test_restore_lockdown_incident_blocks_with_reason_and_audit() -> None:
    app = create_app()
    _override_restore_auth(app)
    audit = FakeAuditService()
    app.dependency_overrides[get_restore_service] = lambda: _build_restore_service(
        FakePolicyServiceAllow(),
        audit,
        FakeIncidentService(IncidentLevel.LOCKDOWN),
    )
    client = TestClient(app)

    response = client.post(
        '/api/v1/restores',
        json={'backup_id': 'backup-0001'},
        headers={'X-API-Key': 'valid', 'X-MFA-Token': 'mfa:admin-key'},
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload['error']['code'] == 'RESTORE_RESTRICTED'
    assert payload['data']['details'][0]['reason_category'] == 'incident_lockdown'
    assert audit.restore_events and audit.restore_events[-1]['reason'] == 'incident_lockdown'
