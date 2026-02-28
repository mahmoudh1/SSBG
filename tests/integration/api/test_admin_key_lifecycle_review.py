from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from app.api.dependencies import get_audit_service, get_auth_service, get_key_management_service
from app.main import create_app
from app.schemas.auth import ApiKeyPrincipal
from app.services.key_management_service import KeyVersionNotFoundError, KeyVersionSnapshot


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


class FakeKeyManagementService:
    async def list_versions(self) -> list[KeyVersionSnapshot]:
        return [
            KeyVersionSnapshot(
                version_id='P-001',
                is_active=False,
                is_destroyed=True,
                rotated_from_version=None,
                created_by_key_id='admin-key',
                rotation_reason='scheduled',
                created_at=datetime.now(UTC),
                activated_at=datetime.now(UTC),
                destroyed_at=datetime.now(UTC),
            ),
        ]

    async def get_version(self, version_id: str) -> KeyVersionSnapshot:
        if version_id != 'P-001':
            raise KeyVersionNotFoundError(version_id)
        return KeyVersionSnapshot(
            version_id='P-001',
            is_active=False,
            is_destroyed=True,
            rotated_from_version=None,
            created_by_key_id='admin-key',
            rotation_reason='scheduled',
            created_at=datetime.now(UTC),
            activated_at=datetime.now(UTC),
            destroyed_at=datetime.now(UTC),
        )

    async def get_crypto_shred_outcome(self, version_id: str) -> dict[str, object]:
        if version_id != 'P-001':
            raise KeyVersionNotFoundError(version_id)
        return {
            'version_id': 'P-001',
            'key_destroyed': True,
            'destroyed_at': datetime.now(UTC),
            'total_backups': 4,
            'irreversible_backups': 4,
            'active_backups': 0,
            'processing_backups': 0,
            'failed_backups': 0,
            'last_shredded_at': datetime.now(UTC),
            'irreversible_reason': 'crypto_shredded',
        }


def test_admin_can_review_key_lifecycle_and_crypto_shred_outcomes() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            _ = (raw_key, client_ip)
            return ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')

    app = create_app()
    audit = FakeAuditService()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_key_management_service] = lambda: FakeKeyManagementService()
    app.dependency_overrides[get_audit_service] = lambda: audit
    client = TestClient(app)

    list_response = client.get('/api/v1/admin/keys/versions', headers={'X-API-Key': 'valid'})
    detail_response = client.get(
        '/api/v1/admin/keys/versions/P-001',
        headers={'X-API-Key': 'valid'},
    )
    outcome_response = client.get(
        '/api/v1/admin/keys/versions/P-001/crypto-shred-outcome',
        headers={'X-API-Key': 'valid'},
    )

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert outcome_response.status_code == 200
    assert detail_response.json()['data']['version']['version_id'] == 'P-001'
    assert outcome_response.json()['data']['version_id'] == 'P-001'
    assert outcome_response.json()['data']['irreversible_backups'] == 4
    assert 'key_bytes' not in str(list_response.json())
    assert 'key_bytes' not in str(detail_response.json())
    assert 'key_bytes' not in str(outcome_response.json())
    actions = [item['action'] for item in audit.actions]
    assert 'key_versions_reviewed' in actions
    assert 'key_version_reviewed' in actions
    assert 'crypto_shred_outcome_reviewed' in actions


def test_review_endpoints_return_404_for_unknown_key_version() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            _ = (raw_key, client_ip)
            return ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_key_management_service] = lambda: FakeKeyManagementService()
    client = TestClient(app)

    detail_response = client.get(
        '/api/v1/admin/keys/versions/P-404',
        headers={'X-API-Key': 'valid'},
    )
    outcome_response = client.get(
        '/api/v1/admin/keys/versions/P-404/crypto-shred-outcome',
        headers={'X-API-Key': 'valid'},
    )

    assert detail_response.status_code == 404
    assert detail_response.json()['error']['code'] == 'KEY_VERSION_NOT_FOUND'
    assert outcome_response.status_code == 404
    assert outcome_response.json()['error']['code'] == 'KEY_VERSION_NOT_FOUND'


def test_operator_denied_review_endpoints_by_rbac() -> None:
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

    list_response = client.get('/api/v1/admin/keys/versions', headers={'X-API-Key': 'valid'})
    detail_response = client.get(
        '/api/v1/admin/keys/versions/P-001',
        headers={'X-API-Key': 'valid'},
    )
    outcome_response = client.get(
        '/api/v1/admin/keys/versions/P-001/crypto-shred-outcome',
        headers={'X-API-Key': 'valid'},
    )

    assert list_response.status_code == 403
    assert detail_response.status_code == 403
    assert outcome_response.status_code == 403
    assert list_response.json() == {
        'error': {'code': 'POLICY_DENIED', 'message': 'Not authorized for this operation'},
        'data': None,
        'meta': {'request_id': 'generated-placeholder-id'},
    }
    assert len(audit.denies) == 3
