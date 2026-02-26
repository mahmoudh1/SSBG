from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from app.api.dependencies import get_api_keys_repository, get_audit_service, get_auth_service
from app.main import create_app
from app.schemas.auth import ApiKeyPrincipal


class FakeAuditService:
    def __init__(self) -> None:
        self.actions: list[dict[str, Any]] = []
        self.denies: list[dict[str, Any]] = []

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


class FakeKeysRepository:
    def __init__(self) -> None:
        self.records: list[Any] = []

    async def create_key(self, record: Any) -> Any:
        if record.created_at is None:
            record.created_at = datetime.now(timezone.utc)
        self.records.append(record)
        return record

    async def list_keys(self) -> list[Any]:
        return list(self.records)

    async def revoke_key(self, key_id: str) -> Any | None:
        for record in self.records:
            if record.key_id == key_id:
                record.is_active = False
                return record
        return None


def test_admin_key_create_list_and_revoke() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            return ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')

    app = create_app()
    audit = FakeAuditService()
    repo = FakeKeysRepository()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_api_keys_repository] = lambda: repo
    app.dependency_overrides[get_audit_service] = lambda: audit
    client = TestClient(app)

    response = client.post(
        '/api/v1/admin/keys',
        json={'role': 'operator', 'department': 'IT', 'description': 'seed'},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 200
    data = response.json()['data']
    assert data['api_key']
    created_key_id = data['key']['key_id']

    response = client.get('/api/v1/admin/keys', headers={'X-API-Key': 'valid'})

    assert response.status_code == 200
    keys = response.json()['data']['keys']
    assert keys[0]['key_id'] == created_key_id
    assert 'api_key' not in keys[0]

    response = client.post(
        f'/api/v1/admin/keys/{created_key_id}/revoke',
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 200
    assert response.json()['data']['key']['is_active'] is False
    assert {'action': 'api_key_created'} in [{'action': item['action']} for item in audit.actions]
    assert {'action': 'api_key_listed'} in [{'action': item['action']} for item in audit.actions]
    assert {'action': 'api_key_revoked'} in [{'action': item['action']} for item in audit.actions]


def test_operator_denied_admin_key_create() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            return ApiKeyPrincipal(key_id='op-key', role='operator', department='IT')

    app = create_app()
    audit = FakeAuditService()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_audit_service] = lambda: audit
    client = TestClient(app)

    response = client.post(
        '/api/v1/admin/keys',
        json={'role': 'operator', 'department': 'IT'},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 403
    assert response.json() == {
        'error': {'code': 'POLICY_DENIED', 'message': 'Not authorized for this operation'},
        'data': None,
        'meta': {'request_id': 'generated-placeholder-id'},
    }
    assert audit.denies
    assert audit.denies[0]['permission'] == 'admin'


def test_operator_denied_admin_key_list_and_revoke() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            return ApiKeyPrincipal(key_id='op-key', role='operator', department='IT')

    app = create_app()
    audit = FakeAuditService()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_audit_service] = lambda: audit
    client = TestClient(app)

    list_response = client.get('/api/v1/admin/keys', headers={'X-API-Key': 'valid'})
    revoke_response = client.post(
        '/api/v1/admin/keys/some-key/revoke',
        headers={'X-API-Key': 'valid'},
    )

    assert list_response.status_code == 403
    assert revoke_response.status_code == 403
    assert len(audit.denies) == 2
