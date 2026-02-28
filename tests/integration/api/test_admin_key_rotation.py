from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from app.api.dependencies import get_audit_service, get_auth_service, get_key_management_service
from app.main import create_app
from app.schemas.auth import ApiKeyPrincipal
from app.services.key_management_service import KeyRotationError, KeyVersionSnapshot


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


class FakeKeyManagementService:
    async def rotate_active_version(
        self,
        to_version_id: str,
        actor_key_id: str | None,
        reason: str | None,
        client_ip: str | None,
    ) -> KeyVersionSnapshot:
        _ = (actor_key_id, reason, client_ip)
        if to_version_id == 'bad':
            raise KeyRotationError('Target key material not found', 'key_material_missing')
        return KeyVersionSnapshot(
            version_id=to_version_id,
            is_active=True,
            is_destroyed=False,
            rotated_from_version='P-001',
            created_by_key_id='admin-key',
            rotation_reason=reason,
            created_at=datetime.now(UTC),
            activated_at=datetime.now(UTC),
            destroyed_at=None,
        )

    async def list_versions(self) -> list[KeyVersionSnapshot]:
        return []


def test_admin_can_rotate_key_version() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            _ = (raw_key, client_ip)
            return ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_key_management_service] = lambda: FakeKeyManagementService()
    client = TestClient(app)

    response = client.post(
        '/api/v1/admin/keys/versions/rotate',
        json={'to_version_id': 'P-002', 'reason': 'scheduled'},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['data']['version']['version_id'] == 'P-002'
    assert payload['data']['version']['is_active'] is True


def test_invalid_rotation_returns_documented_error() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            _ = (raw_key, client_ip)
            return ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_key_management_service] = lambda: FakeKeyManagementService()
    client = TestClient(app)

    response = client.post(
        '/api/v1/admin/keys/versions/rotate',
        json={'to_version_id': 'bad'},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload['error']['code'] == 'KEY_ROTATION_INVALID'
    assert payload['data']['details'][0]['reason_category'] == 'key_material_missing'


def test_operator_denied_key_rotation() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            _ = (raw_key, client_ip)
            return ApiKeyPrincipal(key_id='op-key', role='operator', department='IT')

    app = create_app()
    audit = FakeAuditService()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_key_management_service] = lambda: FakeKeyManagementService()
    app.dependency_overrides[get_audit_service] = lambda: audit
    client = TestClient(app)

    response = client.post(
        '/api/v1/admin/keys/versions/rotate',
        json={'to_version_id': 'P-002'},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 403
    assert response.json() == {
        'error': {'code': 'POLICY_DENIED', 'message': 'Not authorized for this operation'},
        'data': None,
        'meta': {'request_id': 'generated-placeholder-id'},
    }
    assert audit.denies and audit.denies[0]['permission'] == 'admin'
