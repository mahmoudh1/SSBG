from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.api.dependencies import get_audit_service, get_auth_service
from app.main import create_app
from app.schemas.auth import ApiKeyPrincipal


class FakeAuditService:
    def __init__(self) -> None:
        self.denies: list[dict[str, Any]] = []

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


def test_operator_denied_on_restore() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            return ApiKeyPrincipal(key_id='key-1', role='operator', department='IT')

    app = create_app()
    audit = FakeAuditService()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_audit_service] = lambda: audit
    client = TestClient(app)

    response = client.post('/api/v1/restores', headers={'X-API-Key': 'valid'})

    assert response.status_code == 403
    assert response.json() == {
        'error': {'code': 'POLICY_DENIED', 'message': 'Not authorized for this operation'},
        'data': None,
        'meta': {'request_id': 'generated-placeholder-id'},
    }
    assert audit.denies
    assert audit.denies[0]['permission'] == 'restores'


def test_admin_allowed_on_restore() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            return ApiKeyPrincipal(key_id='key-1', role='admin', department='IT')

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    client = TestClient(app)

    response = client.post('/api/v1/restores', headers={'X-API-Key': 'valid'})

    assert response.status_code == 200
    assert response.json() == {'message': 'Restore endpoint placeholder'}


def test_operator_denied_on_admin_endpoint() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            return ApiKeyPrincipal(key_id='key-1', role='operator', department='IT')

    app = create_app()
    audit = FakeAuditService()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_audit_service] = lambda: audit
    client = TestClient(app)

    response = client.get('/api/v1/admin/alerts', headers={'X-API-Key': 'valid'})

    assert response.status_code == 403
    assert response.json() == {
        'error': {'code': 'POLICY_DENIED', 'message': 'Not authorized for this operation'},
        'data': None,
        'meta': {'request_id': 'generated-placeholder-id'},
    }
    assert audit.denies
    assert audit.denies[0]['permission'] == 'admin'
