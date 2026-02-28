from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.api.dependencies import get_audit_service, get_auth_service, get_key_management_service
from app.main import create_app
from app.schemas.auth import ApiKeyPrincipal
from app.services.key_management_service import CryptoShredError


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
    async def execute_crypto_shred(
        self,
        version_id: str,
        principal: ApiKeyPrincipal | None,
        mfa_token: str | None,
        confirmation: str,
        client_ip: str | None,
    ) -> dict[str, object]:
        _ = (principal, client_ip)
        if version_id == 'P-404':
            raise CryptoShredError('Key version not found', 'key_not_found')
        if mfa_token is None:
            raise CryptoShredError('MFA token required', 'mfa_required')
        if confirmation != f'DESTROY {version_id}':
            raise CryptoShredError('Explicit confirmation mismatch', 'missing_confirmation')
        return {
            'version_id': version_id,
            'destroyed': True,
            'affected_backups': 2,
            'incident_effect': 'escalated_to_lockdown',
        }


def test_super_admin_crypto_shred_success_response() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            _ = (raw_key, client_ip)
            return ApiKeyPrincipal(key_id='super-key', role='super_admin', department='Security')

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_key_management_service] = lambda: FakeKeyManagementService()
    client = TestClient(app)

    response = client.post(
        '/api/v1/admin/keys/versions/P-001/crypto-shred',
        json={'confirmation': 'DESTROY P-001'},
        headers={'X-API-Key': 'valid', 'X-MFA-Token': 'mfa:super-key'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['data']['version_id'] == 'P-001'
    assert payload['data']['destroyed'] is True
    assert payload['data']['affected_backups'] == 2


def test_crypto_shred_missing_mfa_returns_documented_error() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            _ = (raw_key, client_ip)
            return ApiKeyPrincipal(key_id='super-key', role='super_admin', department='Security')

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_key_management_service] = lambda: FakeKeyManagementService()
    client = TestClient(app)

    response = client.post(
        '/api/v1/admin/keys/versions/P-001/crypto-shred',
        json={'confirmation': 'DESTROY P-001'},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload['error']['code'] == 'CRYPTO_SHRED_DENIED'
    assert payload['data']['details'][0]['reason_category'] == 'mfa_required'


def test_operator_denied_crypto_shred_by_rbac() -> None:
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
        '/api/v1/admin/keys/versions/P-001/crypto-shred',
        json={'confirmation': 'DESTROY P-001'},
        headers={'X-API-Key': 'valid', 'X-MFA-Token': 'mfa:op-key'},
    )

    assert response.status_code == 403
    assert response.json() == {
        'error': {'code': 'POLICY_DENIED', 'message': 'Not authorized for this operation'},
        'data': None,
        'meta': {'request_id': 'generated-placeholder-id'},
    }
    assert audit.denies and audit.denies[0]['permission'] == 'admin'


def test_crypto_shred_unknown_key_version_returns_not_found() -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            _ = (raw_key, client_ip)
            return ApiKeyPrincipal(key_id='super-key', role='super_admin', department='Security')

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_key_management_service] = lambda: FakeKeyManagementService()
    client = TestClient(app)

    response = client.post(
        '/api/v1/admin/keys/versions/P-404/crypto-shred',
        json={'confirmation': 'DESTROY P-404'},
        headers={'X-API-Key': 'valid', 'X-MFA-Token': 'mfa:super-key'},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload['error']['code'] == 'CRYPTO_SHRED_DENIED'
    assert payload['data']['details'][0]['reason_category'] == 'key_not_found'
