from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from app.api.dependencies import get_audit_service, get_auth_service, get_incident_service
from app.main import create_app
from app.schemas.auth import ApiKeyPrincipal
from app.services.incident_service import IncidentService


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


class FakeAuditService:
    def __init__(self) -> None:
        self.actions: list[dict[str, object]] = []
        self.denies: list[dict[str, object]] = []

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

    async def record_authorization_denied(
        self,
        key_id: str | None,
        role: str,
        permission: str,
        reason: str,
        client_ip: str | None,
    ) -> None:
        self.denies.append(
            {
                'key_id': key_id,
                'role': role,
                'permission': permission,
                'reason': reason,
                'client_ip': client_ip,
            },
        )


def _override_auth(app: Any, role: str) -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            _ = (raw_key, client_ip)
            return ApiKeyPrincipal(key_id='key-1', role=role, department='IT')

    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()


def _build_incident_service(repository: InMemoryIncidentRepository) -> IncidentService:
    settings = SimpleNamespace(current_incident_level='NORMAL')
    return IncidentService(settings, repository)  # type: ignore[arg-type]


def test_authorized_responder_can_read_and_transition_incident_state() -> None:
    app = create_app()
    _override_auth(app, role='admin')
    repository = InMemoryIncidentRepository()
    audit = FakeAuditService()
    app.dependency_overrides[get_incident_service] = lambda: _build_incident_service(repository)
    app.dependency_overrides[get_audit_service] = lambda: audit
    client = TestClient(app)

    read_response = client.get('/api/v1/admin/incident', headers={'X-API-Key': 'valid'})
    assert read_response.status_code == 200
    assert read_response.json()['data']['level'] == 'NORMAL'

    update_response = client.put(
        '/api/v1/admin/incident',
        json={'level': 'QUARANTINE', 'reason': 'investigation'},
        headers={'X-API-Key': 'valid'},
    )
    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload['data']['level'] == 'QUARANTINE'
    assert payload['data']['reason'] == 'investigation'
    assert {'action': 'incident_level_changed'} in [
        {'action': item['action']} for item in audit.actions
    ]


def test_invalid_transition_is_denied_with_documented_error() -> None:
    app = create_app()
    _override_auth(app, role='admin')
    repository = InMemoryIncidentRepository()
    audit = FakeAuditService()
    repository.records.append(
        SimpleNamespace(
            level='LOCKDOWN',
            changed_by_key_id='key-1',
            reason='critical',
            changed_at=datetime.now(UTC),
        ),
    )
    app.dependency_overrides[get_incident_service] = lambda: _build_incident_service(repository)
    app.dependency_overrides[get_audit_service] = lambda: audit
    client = TestClient(app)

    response = client.put(
        '/api/v1/admin/incident',
        json={'level': 'NORMAL'},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload['error']['code'] == 'INCIDENT_TRANSITION_INVALID'
    assert payload['data']['details'][0]['reason_category'] == 'invalid_transition'


def test_unauthorized_incident_transition_is_denied() -> None:
    app = create_app()
    _override_auth(app, role='operator')
    audit = FakeAuditService()
    app.dependency_overrides[get_audit_service] = lambda: audit
    client = TestClient(app)

    response = client.put(
        '/api/v1/admin/incident',
        json={'level': 'QUARANTINE'},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 403
    assert response.json() == {
        'error': {'code': 'POLICY_DENIED', 'message': 'Not authorized for this operation'},
        'data': None,
        'meta': {'request_id': 'generated-placeholder-id'},
    }
    assert audit.denies and audit.denies[0]['permission'] == 'admin'
