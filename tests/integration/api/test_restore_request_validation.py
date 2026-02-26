from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_auth_service, get_restore_service
from app.main import create_app
from app.schemas.auth import ApiKeyPrincipal
from app.services.restore_service import RestoreIntegrityFailed, RestoreMetadataNotFound


class FakeBackupsRepository:
    def __init__(self, metadata: object | None) -> None:
        self.metadata = metadata
        self.lookups: list[str] = []

    async def get_by_backup_id(self, backup_id: str) -> object | None:
        self.lookups.append(backup_id)
        if self.metadata is None:
            return None
        if getattr(self.metadata, 'backup_id', None) == backup_id:
            return self.metadata
        return None


def _override_admin_auth(app: FastAPI) -> None:
    class FakeAuthService:
        async def authenticate(self, raw_key: str, client_ip: str | None) -> ApiKeyPrincipal:
            return ApiKeyPrincipal(key_id='admin-key', role='admin', department='IT')

    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()


class FakeRestoreService:
    async def load_restore_metadata(
        self,
        request: object,
        principal: object,
        client_ip: str | None,
        mfa_token: str | None,
    ) -> dict[str, object]:
        _ = (request, principal, client_ip)
        if not mfa_token:
            from app.services.auth_service import MfaFailure

            raise MfaFailure('MFA_REQUIRED', 'MFA token required')
        return {
            'status': 'metadata_loaded',
            'backup': {
                'backup_id': 'backup-0001',
                'classification': 'CONFIDENTIAL',
                'source_system': 'system-a',
                'status': 'ACTIVE',
                'key_version': 'P-001',
                'created_at': datetime(2026, 2, 26, tzinfo=timezone.utc).isoformat(),
            },
            'next_step': 'mfa_policy_authorization',
        }


class FakeRestoreNotFoundService:
    async def load_restore_metadata(
        self,
        request: object,
        principal: object,
        client_ip: str | None,
        mfa_token: str | None,
    ) -> dict[str, object]:
        _ = (request, principal, client_ip, mfa_token)
        raise RestoreMetadataNotFound('backup-0001')


class FakeRestoreIntegrityFailureService:
    async def load_restore_metadata(
        self,
        request: object,
        principal: object,
        client_ip: str | None,
        mfa_token: str | None,
    ) -> dict[str, object]:
        _ = (request, principal, client_ip, mfa_token)
        raise RestoreIntegrityFailed()


def test_restore_invalid_request_returns_validation_contract() -> None:
    app = create_app()
    _override_admin_auth(app)
    client = TestClient(app)

    response = client.post(
        '/api/v1/restores',
        json={'backup_id': 'short'},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload['error']['code'] == 'VALIDATION_ERROR'
    assert payload['meta']['request_id'] == 'generated-placeholder-id'
    assert payload['data']['details']


def test_restore_metadata_not_found_returns_documented_error_and_no_token() -> None:
    app = create_app()
    _override_admin_auth(app)
    app.dependency_overrides[get_restore_service] = lambda: FakeRestoreNotFoundService()
    client = TestClient(app)

    response = client.post(
        '/api/v1/restores',
        json={'backup_id': 'backup-0001'},
        headers={'X-API-Key': 'valid'},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload['error']['code'] == 'RESTORE_BACKUP_NOT_FOUND'
    assert payload['data']['details'] == [{'backup_id': 'backup-0001'}]
    assert 'restore_token' not in payload.get('data', {})


def test_restore_valid_request_loads_backup_metadata_without_token() -> None:
    app = create_app()
    _override_admin_auth(app)
    app.dependency_overrides[get_restore_service] = lambda: FakeRestoreService()
    client = TestClient(app)

    response = client.post(
        '/api/v1/restores',
        json={'backup_id': 'backup-0001', 'reason': 'investigation'},
        headers={'X-API-Key': 'valid', 'X-MFA-Token': 'mfa:admin-key'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['data']['status'] == 'metadata_loaded'
    assert payload['data']['backup']['backup_id'] == 'backup-0001'
    assert payload['data']['backup']['classification'] == 'CONFIDENTIAL'
    assert payload['data']['next_step'] == 'mfa_policy_authorization'
    assert 'restore_token' not in payload['data']


def test_restore_integrity_failure_returns_documented_error_and_no_token() -> None:
    app = create_app()
    _override_admin_auth(app)
    app.dependency_overrides[get_restore_service] = lambda: FakeRestoreIntegrityFailureService()
    client = TestClient(app)

    response = client.post(
        '/api/v1/restores',
        json={'backup_id': 'backup-0001'},
        headers={'X-API-Key': 'valid', 'X-MFA-Token': 'mfa:admin-key'},
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload['error']['code'] == 'RESTORE_INTEGRITY_FAILED'
    assert 'restore_token' not in payload.get('data', {})
